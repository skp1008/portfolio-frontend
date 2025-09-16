"""
FastAPI backend for SQL Query Generator Chatbot.
Based on llm_app.py but adapted for web interface with chat functionality.
Runs on port 8002.
"""

import os
import re
import json
import uuid
import sys
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

try:
    from llama_index.core import StorageContext, load_index_from_storage
    try:
        from llama_index.core.settings import Settings  # preferred across versions
    except Exception:
        from llama_index.core import Settings  # fallback for versions that re-export
    from llama_index.llms.openai_like import OpenAILike
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    LLAMA_INDEX_AVAILABLE = True
except ImportError as e:
    print(f"Warning: llama-index not installed. Please install with: pip install llama-index llama-index-llms-openai-like llama-index-embeddings-huggingface")
    print(f"Error: {e}")
    LLAMA_INDEX_AVAILABLE = False
    # Create mock classes for basic operation
    class MockSettings:
        embed_model = None
        llm = None
    Settings = MockSettings()

# Import the MCP handler
try:
    from mcp_handler import MCPHandler
except ImportError:
    print("Warning: MCP handler not found. Some features may be limited.")
    MCPHandler = None

# Together AI configuration
# Stronger default model (overridable via env)
MODEL_NAME = os.getenv("TOGETHER_MODEL", "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo")
API_BASE = "https://api.together.xyz/v1"

app = FastAPI(title="SQL Query Generator Chatbot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Resolve absolute paths for static frontend directory
BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"
# Feedback lessons store (persisted across runs)
FEEDBACK_PATH = (BASE_DIR / "SQL_App" / "feedback_store.json")
def load_feedback_lessons() -> str:
    try:
        if FEEDBACK_PATH.exists():
            data = json.loads(FEEDBACK_PATH.read_text(encoding="utf-8"))
            lessons = data.get("lessons", [])
            if lessons:
                return "\n".join(f"- {l}" for l in lessons[:100])
    except Exception as _:
        pass
    return ""

def append_feedback_lesson(lesson: str) -> None:
    try:
        FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {"lessons": []}
        if FEEDBACK_PATH.exists():
            try:
                payload = json.loads(FEEDBACK_PATH.read_text(encoding="utf-8"))
            except Exception:
                payload = {"lessons": []}
        lessons = payload.get("lessons", [])
        if lesson and lesson not in lessons:
            lessons.insert(0, lesson)
            payload["lessons"] = lessons[:500]
            FEEDBACK_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception as _:
        pass


# Mount static files using absolute path so it works on Railway
app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")

# Favicon route for reliability in deployed environment
@app.get("/favicon.ico")
async def favicon():
    return FileResponse(str(FRONTEND_DIR / "logo.png"))

# Serve homepage
@app.get("/")
async def root():
    """Serve the main website."""
    return FileResponse(str(FRONTEND_DIR / "website2.html"))

# Data models
class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime
    sql_query: Optional[str] = None
    explanation: Optional[str] = None

class ChatSession(BaseModel):
    session_id: str
    title: str
    created_at: datetime
    last_updated: datetime
    messages: List[ChatMessage]
    metadata: Optional[Dict[str, str]] = None

class QueryRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class QueryResponse(BaseModel):
    session_id: str
    sql_query: str
    explanation: str
    message_id: str

# Global variables
query_engine = None
mcp_handler = None
query_validator = None
index = None

# Chat data storage
CHAT_DATA_DIR = Path("chatbot_data")
CHAT_DATA_DIR.mkdir(exist_ok=True)

# -------- TEMP SEAL (deployed only) --------
# Remove this line (or set to False) to unseal the online SQL generator.
CHATBOT_SEALED = True

# Schema validation - focus on known problematic patterns
KNOWN_HALLUCINATIONS = {
    "banned_columns": [
        "AP_AMOUNT",      # Should be AMOUNT
        "AP_REFERENCE",   # Should be REFERENCE  
    ],
    "banned_patterns": [
        r"EXTRACT\s*\(\s*YEAR\s+FROM\s+DATE_STAMP\s*\)",  # Should be BILL_YEAR
        r"YEAR\s*\(\s*DATE_STAMP\s*\)",                    # Should be BILL_YEAR
    ]
}

# ---------- Schema and formatting helpers ----------
SCHEMA_DIR = BASE_DIR / "SQL_App" / "Schema"

def _load_schema_index() -> Dict[str, set]:
    index: Dict[str, set] = {}
    try:
        if SCHEMA_DIR.exists():
            for f in SCHEMA_DIR.glob("*.json"):
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    if isinstance(data, dict):
                        for table, cols in data.items():
                            if isinstance(cols, list):
                                index.setdefault(table.lower(), set()).update(c.lower() for c in cols)
                    elif isinstance(data, list):
                        for item in data:
                            table = str(item.get("table", "")).lower()
                            cols = item.get("columns") or item.get("fields") or []
                            if table:
                                index.setdefault(table, set()).update(str(c).lower() for c in cols)
                except Exception:
                    continue
    except Exception:
        pass
    return index

SCHEMA_INDEX = _load_schema_index()

SQL_CLAUSE_BREAKS = [" select ", " from ", " where ", " group by ", " order by ", " having ", " join ", " left join ", " right join ", " inner join "]

def vertical_format_sql(sql: str) -> str:
    if not sql:
        return sql
    s = " " + sql.strip().replace("\n", " ") + " "
    for kw in SQL_CLAUSE_BREAKS:
        s = s.replace(kw, f"\n{kw.strip().upper()} ")
        s = s.replace(kw.upper(), f"\n{kw.strip().upper()} ")
    s = s.replace(" AND ", "\n  AND ").replace(" and ", "\n  AND ")
    return s.strip()

def check_sql_against_schema(sql: str) -> Optional[str]:
    if not sql or not SCHEMA_INDEX:
        return None
    import re
    pairs = re.findall(r"([A-Za-z_][A-Za-z0-9_]*)\s*\.\s*([A-Za-z_][A-Za-z0-9_]*)", sql)
    for t, c in pairs:
        t_l, c_l = t.lower(), c.lower()
        if t_l not in SCHEMA_INDEX or c_l not in SCHEMA_INDEX.get(t_l, set()):
            return f"Invalid reference: {t}.{c} is not in schema."
    return None

def classify_intent(message: str) -> str:
    m = message.strip().lower()
    if "error" in m and ("line" in m or "column" in m or "syntax" in m):
        return "feedback"
    # simple greeting detector
    if m in {"hi", "hello", "hey", "yo", "sup", "hola"} or m.startswith("hello"):
        return "greet"
    # default to query; rely on LLM reasoning for specifics
    return "query"

def needs_clarification(message: str) -> Optional[str]:
    m = message.lower()
    qs = []
    if "folio" in m and not any(k in m for k in [" active ", " all "]):
        qs.append("Did you want only active folios or all?")
    if "folio" in m and "999-999-99-9" not in m:
        qs.append("Do you want me to remove reference folio 999-999-99-9 from results?")
    return " ".join(qs) if qs else None

def extract_tables(sql: str) -> List[str]:
    if not sql:
        return []
    import re
    tbls = []
    # naive FROM/JOIN capture
    for kw in [" from ", " join ", " from\n", " join\n"]:
        parts = re.split(kw, " " + sql.lower() + " ")
        for i in range(1, len(parts)):
            token = parts[i].strip().split()[0].strip(",")
            if token and token.isidentifier():
                tbls.append(token)
    # unique preserve order
    seen = set()
    ordered = []
    for t in tbls:
        if t not in seen:
            seen.add(t)
            ordered.append(t)
    return ordered

def extract_sql_from_response(response_text):
    """Extract SQL query from response text."""
    import re
    # Look for SQL code blocks
    sql_patterns = [
        r'```sql\s*(.*?)\s*```',
        r'```\s*(SELECT.*?;)\s*```',
        r'(SELECT.*?;)',
    ]
    
    for pattern in sql_patterns:
        matches = re.findall(pattern, response_text, re.DOTALL | re.IGNORECASE)
        if matches:
            return matches[0].strip()
    return None

def validate_schema_adherence(sql_query):
    """Validate that SQL query avoids known hallucination patterns."""
    import re
    if not sql_query:
        return None
    
    # Check for known hallucinated columns
    for banned_col in KNOWN_HALLUCINATIONS["banned_columns"]:
        if re.search(rf'\b{re.escape(banned_col)}\b', sql_query, re.IGNORECASE):
            if banned_col == "AP_AMOUNT":
                return f"Invalid column '{banned_col}' found. Use 'AMOUNT' instead."
            elif banned_col == "AP_REFERENCE":
                return f"Invalid column '{banned_col}' found. Use 'REFERENCE' instead."
            else:
                return f"Invalid column '{banned_col}' found. Check schema for correct column name."
    
    # Check for known problematic patterns
    for pattern in KNOWN_HALLUCINATIONS["banned_patterns"]:
        if re.search(pattern, sql_query, re.IGNORECASE):
            if "EXTRACT" in pattern or "YEAR" in pattern:
                return "Don't use EXTRACT(YEAR FROM DATE_STAMP) or YEAR(DATE_STAMP). Use BILL_YEAR column instead."
            else:
                return f"Problematic pattern detected. Check the schema for correct syntax."
    
    return None

# ---------- Preference building from historical scripts ----------
HIST_DIR = BASE_DIR / "SQL_App" / "Historical_Scripts" / "IMPORTANT"

def build_preferred_tables(limit: int = 50) -> List[str]:
    import re
    counts: Dict[str, int] = {}
    try:
        if HIST_DIR.exists():
            for f in HIST_DIR.rglob("*.*"):
                if not f.is_file():
                    continue
                try:
                    txt = f.read_text(encoding="utf-8", errors="ignore").lower()
                except Exception:
                    continue
                for m in re.findall(r"\bfrom\s+([a-z_][a-z0-9_]+)|\bjoin\s+([a-z_][a-z0-9_]+)", txt):
                    for t in m:
                        if t:
                            counts[t] = counts.get(t, 0) + 1
    except Exception:
        pass
    ordered = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return [t for t, _ in ordered[:limit]]

PREFERRED_TABLES = build_preferred_tables()

# ---------- LLM intent classifier ----------
def llm_classify_intent_llama(message: str, api_key: Optional[str]) -> str:
    try:
        if not api_key:
            return "query"
        llm = OpenAILike(model=MODEL_NAME, api_key=api_key, api_base=API_BASE, temperature=0.0, max_tokens=16)
        prompt = (
            "Classify the user message strictly into one of: greet | feedback | query | irrelevant.\n"
            "- greet: greetings like hi/hello.\n"
            "- feedback: pasted DB error or message about a previous query failing.\n"
            "- query: a request to produce SQL or retrieve data.\n"
            "- irrelevant: anything else.\n"
            f"Message: {message}\nAnswer with one word only."
        )
        out = llm.complete(prompt).text.strip().lower()
        if out in {"greet", "feedback", "query", "irrelevant"}:
            return out
    except Exception:
        pass
    return "query"

class QueryValidator:
    def __init__(self, api_key, api_base="https://api.together.xyz/v1"):
        self.api_key = api_key
        self.api_base = api_base
        self.validator_model = "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"
        
    def setup_validator_llm(self):
        """Set up the validator LLM."""
        return OpenAILike(
            model=self.validator_model,
            api_key=self.api_key,
            api_base=self.api_base,
            temperature=0.0,
            max_tokens=1024,
        )
    
    def extract_sql_query(self, response_text):
        """Extract just the SQL query from the response."""
        sql_patterns = [
            r'```sql\s*(.*?)\s*```',
            r'```\s*(SELECT.*?;)\s*```',
            r'(SELECT.*?;)',
        ]
        
        for pattern in sql_patterns:
            matches = re.findall(pattern, response_text, re.DOTALL | re.IGNORECASE)
            if matches:
                return matches[0].strip()
        
        return response_text.strip()
    
    def validate_and_refine_query(self, user_question, generated_response, mcp_instructions):
        """Validate and refine the generated query using a second model."""
        llm = self.setup_validator_llm()
        
        sql_query = self.extract_sql_query(generated_response)
        
        validation_prompt = f"""
You are a SQL query validator and refiner. Your job is to:

1. Check if the generated query matches the user's exact requirements
2. Fix any issues according to the MCP instructions
3. Return the corrected SQL query AND update the explanation to match

USER QUESTION: {user_question}

GENERATED RESPONSE: {generated_response}

MCP INSTRUCTIONS:
{mcp_instructions}

CRITICAL RULES:
- ONLY implement what the user explicitly asked for
- DO NOT add extra conditions, filters, or business logic unless specifically requested
- If user asks for "sod", use LIKE '%sod%' in reference column
- If user asks for "positive 100 or negative 100", use (amount = 100 OR amount = -100)
- Only include tables and conditions explicitly mentioned by the user
- Use the simplest possible approach
- Start with SELECT, end with semicolon
- Prefer account_number → land_relation → land_legal for addresses

Please analyze the generated query and provide:
1. A corrected SQL query that matches the user's exact requirements
2. An updated explanation that accurately describes what the corrected query does

Format your response as:
```sql
[corrected SQL query]
```

**Explanation:**
[updated explanation that matches the corrected query]
"""
        
        try:
            response = llm.complete(validation_prompt)
            refined_response = response.text.strip()
            
            refined_query = self.extract_sql_query(refined_response)
            
            explanation_patterns = [
                r'\*\*Explanation:\*\*(.*?)(?=\n\n|$)',
                r'Explanation:\s*(.*?)(?=\n\n|$)',
                r'Brief explanation:\s*(.*?)(?=\n\n|$)',
                r'(?:This query|The query|Query explanation):\s*(.*?)(?=\n\n|$)'
            ]
            
            refined_explanation = ""
            for pattern in explanation_patterns:
                explanation_match = re.search(pattern, refined_response, re.DOTALL | re.IGNORECASE)
                if explanation_match:
                    refined_explanation = explanation_match.group(1).strip()
                    break
            
            if not refined_explanation:
                sql_end = refined_response.find('```', refined_response.find('```') + 3)
                if sql_end != -1:
                    remaining_text = refined_response[sql_end + 3:].strip()
                    if remaining_text and len(remaining_text) > 10:
                        refined_explanation = remaining_text[:200] + ("..." if len(remaining_text) > 200 else "")
            
            return refined_query, refined_explanation
            
        except Exception as e:
            print(f"⚠️  Query validation failed: {e}")
            return sql_query, ""

def initialize_query_engine():
    """Initialize the RAG query engine and related components."""
    global query_engine, mcp_handler, query_validator, index
    
    if not LLAMA_INDEX_AVAILABLE:
        print("[ERROR] llama-index not available. Please install required packages.")
        return False
    
    try:
        # Set up the embedding model
        embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
        Settings.embed_model = embed_model
        
        # Robustly locate rag_storage across environments
        candidate_paths = [
            BASE_DIR / "SQL_App" / "rag_storage",
            BASE_DIR.parent / "SQL_App" / "rag_storage",
            Path.cwd() / "SQL_App" / "rag_storage",
        ]
        rag_storage_path = None
        for p in candidate_paths:
            if p.exists():
                rag_storage_path = p
                break
        if not rag_storage_path:
            print("[ERROR] RAG storage not found. Attempting to build it now...")
            # Try to run the RAG setup
            try:
                import subprocess
                result = subprocess.run([
                    sys.executable, "setup_deployment.py"
                ], capture_output=True, text=True, timeout=300)  # 5 minute timeout
                
                if result.returncode == 0:
                    # Try to find RAG storage again
                    for p in candidate_paths:
                        if p.exists():
                            rag_storage_path = p
                            break
                    if not rag_storage_path:
                        print("[ERROR] RAG setup completed but storage still not found.")
                        return False
                else:
                    print(f"[ERROR] RAG setup failed: {result.stderr}")
                    return False
            except Exception as setup_error:
                print(f"[ERROR] Error during RAG setup: {setup_error}")
                return False
        
        print(f"[OK] Found RAG storage at: {rag_storage_path}")
        storage_context = StorageContext.from_defaults(persist_dir=str(rag_storage_path))
        index = load_index_from_storage(storage_context)
        
        # API key from environment
        api_key = os.getenv("TOGETHER_API_KEY")
        if not api_key:
            print("[ERROR] TOGETHER_API_KEY not set in environment.")
            return False
        
        # Set up the LLM
        llm = OpenAILike(
            model=MODEL_NAME,
            api_key=api_key,
            api_base=API_BASE,
            temperature=0.0,
            max_tokens=1024,
            request_timeout=120.0,
        )
        
        Settings.llm = llm
        
        # Initialize MCP handler and query validator
        if MCPHandler:
            mcp_handler = MCPHandler()
        else:
            mcp_handler = None
        query_validator = QueryValidator(api_key, API_BASE)
        
        # Create query engine
        query_engine = index.as_query_engine(
            similarity_top_k=3,
            response_mode="compact",
            text_qa_template_str="""Context information is below.
---------------------
{context_str}
---------------------
Task: Determine if the user request is (A) a SQL query request about the database, or (B) a general chat. If (B), answer conversationally and briefly without fabricating data. If (A), do the following exactly:

1) Ask at most one clarification if essential (examples: active vs all folios; exclude reference folio 999-999-99-9; ambiguous column names). If user doesn’t answer, proceed with reasonable defaults: active folios only; exclude 999-999-99-9.
2) Use ONLY tables/columns that exist in the provided schema. If user asks for a non-existent field (e.g., account number in land_legal), tell them and suggest a valid alternative.
3) Prefer tables historically used in prior scripts. If tables have already been chosen and are schema-valid, KEEP those table names and only adjust columns/joins.
3) Format SQL vertically with newlines between clauses and each AND on its own line.
4) After the SQL block, provide a bullet-point explanation listing tables and columns used and the main filter logic.

Question: {query_str}

Response format:
```sql
[Your SQL query here]
```

• Tables and joins used: [...]
• Columns used: [...]
• Filters and logic: [...]
""",
        )
        
        print("[OK] Query engine initialized successfully!")
        return True
        
    except Exception as e:
        print(f"[ERROR] Error loading RAG index: {str(e)}")
        return False

def load_chat_session(session_id: str) -> Optional[ChatSession]:
    """Load a chat session from file."""
    session_file = CHAT_DATA_DIR / f"{session_id}.json"
    if session_file.exists():
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Convert datetime strings back to datetime objects
                if 'created_at' in data and isinstance(data['created_at'], str):
                    try:
                        data['created_at'] = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
                    except ValueError:
                        data['created_at'] = datetime.now()
                if 'last_updated' in data and isinstance(data['last_updated'], str):
                    try:
                        data['last_updated'] = datetime.fromisoformat(data['last_updated'].replace('Z', '+00:00'))
                    except ValueError:
                        data['last_updated'] = datetime.now()
                if 'messages' in data:
                    for msg in data['messages']:
                        if 'timestamp' in msg and isinstance(msg['timestamp'], str):
                            try:
                                msg['timestamp'] = datetime.fromisoformat(msg['timestamp'].replace('Z', '+00:00'))
                            except ValueError:
                                msg['timestamp'] = datetime.now()
                return ChatSession(**data)
        except Exception as e:
            print(f"Error loading session {session_id}: {e}")
    return None

def save_chat_session(session: ChatSession):
    """Save a chat session to file."""
    session_file = CHAT_DATA_DIR / f"{session.session_id}.json"
    try:
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(session.dict(), f, indent=2, default=str)
    except Exception as e:
        print(f"Error saving session {session.session_id}: {e}")

def get_all_chat_sessions() -> List[Dict]:
    """Get all chat sessions for the sidebar."""
    sessions = []
    for session_file in CHAT_DATA_DIR.glob("*.json"):
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                sessions.append({
                    "session_id": data["session_id"],
                    "title": data["title"],
                    "last_updated": data["last_updated"]
                })
        except Exception as e:
            print(f"Error loading session {session_file}: {e}")
    
    # Sort by last_updated descending
    sessions.sort(key=lambda x: x["last_updated"], reverse=True)
    return sessions

def create_session_title(first_message: str) -> str:
    """Create a concise title from the first message."""
    # Take first 50 characters and clean up
    title = first_message[:50].strip()
    if len(first_message) > 50:
        title += "..."
    return title

@app.on_event("startup")
async def startup_event():
    """Initialize the query engine on startup."""
    success = initialize_query_engine()
    if not success:
        print("⚠️ Failed to initialize query engine. Some features may not work.")

@app.get("/")
async def root():
    """Serve the main website."""
    return FileResponse(str(FRONTEND_DIR / "website2.html"))

@app.get("/meter-form-processor")
async def meter_form_processor():
    """Serve the meter form processor page."""
    return FileResponse(str(FRONTEND_DIR / "meter-form-processor.html"))

@app.get("/single-occupancy-discount")
async def single_occupancy_discount():
    """Serve the single occupancy discount page."""
    return FileResponse(str(FRONTEND_DIR / "single-occupancy-discount.html"))

@app.get("/secondary-suite-exemption")
async def secondary_suite_exemption():
    """Serve the secondary suite exemption page."""
    return FileResponse(str(FRONTEND_DIR / "secondary-suite-exemption.html"))

@app.get("/water-consumption-anomaly")
async def water_consumption_anomaly():
    """Serve the water consumption anomaly page."""
    return FileResponse(str(FRONTEND_DIR / "water-consumption-anomaly.html"))

@app.get("/sql-query-generator")
async def sql_query_generator():
    """Serve the SQL query generator page."""
    return FileResponse(str(FRONTEND_DIR / "sql-query-generator.html"))

@app.get("/projects")
async def projects_page():
    """Serve the projects page."""
    return FileResponse(str(FRONTEND_DIR / "projects.html"))

@app.get("/health")
async def health_check():
    api_key_present = bool(os.getenv("TOGETHER_API_KEY"))
    rag_paths = [
        str(BASE_DIR / "SQL_App" / "rag_storage"),
        str(BASE_DIR.parent / "SQL_App" / "rag_storage"),
        str(Path.cwd() / "SQL_App" / "rag_storage"),
    ]
    existing_rag_path = next((p for p in rag_paths if Path(p).exists()), None)
    
    # Check if RAG storage files exist
    rag_files_exist = False
    if existing_rag_path:
        required_files = ["docstore.json", "index_store.json", "default__vector_store.json"]
        rag_files_exist = all(Path(existing_rag_path) / file for file in required_files)
    
    # Check chat data directory
    chat_data_exists = Path("chatbot_data").exists()
    
    return {
        "status": "healthy",
        "service": "sql_chatbot_backend",
        "llama_index_available": LLAMA_INDEX_AVAILABLE,
        "query_engine_initialized": query_engine is not None,
        "api_key_present": api_key_present,
        "rag_storage_path": existing_rag_path,
        "rag_files_exist": rag_files_exist,
        "chat_data_exists": chat_data_exists,
        "frontend_dir": str(FRONTEND_DIR),
        "deployment_ready": query_engine is not None and api_key_present and rag_files_exist,
    }

@app.get("/sessions")
async def get_sessions():
    """Get all chat sessions for the sidebar."""
    return {"sessions": get_all_chat_sessions()}

@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get a specific chat session."""
    session = load_chat_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@app.post("/query")
async def process_query(request: QueryRequest):
    """Process a SQL query request."""
    global query_engine, mcp_handler, query_validator
    
    # If sealed, always deny while keeping the backend intact
    if CHATBOT_SEALED:
        return QueryResponse(
            session_id=request.session_id or str(uuid.uuid4()),
            sql_query="",
            explanation="ACCESS DENIED",
            message_id=str(uuid.uuid4())
        )

    if not query_engine:
        raise HTTPException(status_code=500, detail="Query engine not initialized")
    
    try:
        # Get or create session
        if request.session_id:
            session = load_chat_session(request.session_id)
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
        else:
            # Create new session
            session_id = str(uuid.uuid4())
            session = ChatSession(
                session_id=session_id,
                title=create_session_title(request.message),
                created_at=datetime.now(),
                last_updated=datetime.now(),
                messages=[]
            )
        
        # Add user message
        user_message = ChatMessage(
            role="user",
            content=request.message,
            timestamp=datetime.now()
        )
        session.messages.append(user_message)
        
        # Determine intent and optionally ask a single clarification
        # Hybrid intent: light LLM classifier first, then safe fallback
        api_key = os.getenv("TOGETHER_API_KEY")
        intent = llm_classify_intent_llama(request.message, api_key)
        if intent not in {"greet", "feedback", "query", "irrelevant"}:
            intent = classify_intent(request.message)
        if intent == "greet":
            chat_reply = "Hello! I’m here to generate SQL queries for your database. Describe the data you want and I’ll create a query, or paste an error you saw and I’ll fix it."
            assistant_message = ChatMessage(
                role="assistant",
                content=chat_reply,
                timestamp=datetime.now()
            )
            session.messages.append(assistant_message)
            session.last_updated = datetime.now()
            save_chat_session(session)
            return QueryResponse(session_id=session.session_id, sql_query="", explanation=chat_reply, message_id=str(uuid.uuid4()))

        if intent == "irrelevant":
            note = "I can only assist with database SQL queries. Please describe the data you want and I’ll build a query for you."
            assistant_message = ChatMessage(role="assistant", content=note, timestamp=datetime.now())
            session.messages.append(assistant_message)
            session.last_updated = datetime.now()
            save_chat_session(session)
            return QueryResponse(session_id=session.session_id, sql_query="", explanation=note, message_id=str(uuid.uuid4()))

        if intent == "feedback":
            # Store lesson from user error report and acknowledge
            append_feedback_lesson(f"User-reported error/context: {request.message[:500]}")
            assistant_message = ChatMessage(
                role="assistant",
                content="Thanks. I recorded that error and will avoid the pattern next time. Ask again and I will generate a corrected query.",
                timestamp=datetime.now()
            )
            session.messages.append(assistant_message)
            session.last_updated = datetime.now()
            save_chat_session(session)
            return QueryResponse(session_id=session.session_id, sql_query="", explanation="Recorded feedback.", message_id=str(uuid.uuid4()))

        # query intent
        ask = needs_clarification(request.message)
        user_text = request.message
        if ask:
            # Clarify once using defaults if the user does not respond later
            assistant_message = ChatMessage(
                role="assistant",
                content=ask + " (I'll proceed with defaults if not specified.)",
                timestamp=datetime.now()
            )
            session.messages.append(assistant_message)
            # proceed immediately with defaults (active folios; exclude reference folio)
            user_text = request.message + "\nDEFAULTS: active folios; exclude reference folio 999-999-99-9."

        # Add schema context note for RAG system - let RAG provide the authoritative schema + feedback lessons
        schema_note = """
<!--------------------  SCHEMA_INSTRUCTION  ------------------->
IMPORTANT: Use ONLY the column names and table structures provided by the RAG system below.
The RAG system has access to the complete, authoritative database schema.
NEVER invent or assume column names - trust the schema information provided.
<!---------------------  END_INSTRUCTION    ------------------->

"""
        lessons = load_feedback_lessons()
        if lessons:
            schema_note += "\n<!----- FEEDBACK LESSONS ----->\n" + lessons + "\n<!----- END LESSONS ----->\n"
        context_query = schema_note + user_text
        
        # Process query
        locked_tables: List[str] = []
        try:
            response = query_engine.query(context_query)
            response_text = response.response
            # lock tables chosen in the first successful attempt if they are schema-valid
            try:
                _init_sql = extract_sql_from_response(response_text)
                if _init_sql:
                    _init_tbls = extract_tables(_init_sql)
                    locked_tables = [t for t in _init_tbls if t in SCHEMA_INDEX]
            except Exception:
                locked_tables = []
            
            # Validate schema adherence and formatting
            sql_query = extract_sql_from_response(response_text)
            if sql_query:
                validation_errors = validate_schema_adherence(sql_query)
                if validation_errors:
                    # Regenerate with validation errors
                    error_prompt = f"{context_query}\n\nERROR: {validation_errors}\nPlease fix the query above to use only valid column names from the schema."
                    response = query_engine.query(error_prompt)
                    response_text = response.response
                # hard schema check
                schema_err = check_sql_against_schema(sql_query)
                if schema_err:
                    error_prompt = f"{context_query}\n\nERROR: {schema_err}\nRegenerate using only schema-valid table.column references."
                    response = query_engine.query(error_prompt)
                    response_text = response.response
                    
        except Exception as e:
            print(f"Query engine error: {e}")
            if "context size" in str(e).lower() and index:
                # Fallback with minimal retrieval
                try:
                    minimal_engine = index.as_query_engine(similarity_top_k=1, response_mode="compact")
                    response = minimal_engine.query(context_query)
                    response_text = response.response
                except Exception as fallback_error:
                    print(f"Fallback query also failed: {fallback_error}")
                    # Provide a basic fallback response
                    response_text = f"""```sql
SELECT * FROM your_table WHERE condition = 'value';
```

**Explanation:**
I encountered an error while processing your request. Please make sure the RAG index is properly built by running 'python SQL_App/rag_code.py' first. This is a fallback response."""
            else:
                # Provide a basic fallback response
                response_text = f"""```sql
SELECT * FROM your_table WHERE condition = 'value';
```

**Explanation:**
I encountered an error while processing your request. Please make sure the RAG index is properly built by running 'python SQL_App/rag_code.py' first. This is a fallback response."""
        
        # Validate and refine with MCP
        mcp_instructions = ""
        if mcp_handler:
            try:
                mcp_instructions = mcp_handler.get_system_prompt()
            except Exception as e:
                print(f"Warning: Could not get MCP instructions: {e}")
                mcp_instructions = ""
        
        try:
            refined_query, refined_explanation = query_validator.validate_and_refine_query(
                request.message, 
                response_text, 
                mcp_instructions
            )
        except Exception as validation_error:
            print(f"Query validation failed: {validation_error}")
            # Fallback to original response
            refined_query = query_validator.extract_sql_query(response_text)
            refined_explanation = "This SQL query retrieves data based on your specific requirements using the appropriate database tables and conditions."
        
        # Enforce vertical formatting and bullet points
        refined_query = vertical_format_sql(refined_query)
        # Lock original tables from the initial attempt if schema-valid
        if locked_tables:
            # If any locked table is missing, regenerate with an explicit constraint
            present_after = extract_tables(refined_query)
            missing = [t for t in locked_tables if t not in present_after]
            if missing:
                constraint_prompt = (
                    f"{context_query}\n\nCRITICAL: Do not change tables. Use exactly these tables: {', '.join(locked_tables)}.\n"
                    "Regenerate the SQL using the same user intent, keeping these base tables unchanged."
                )
                try:
                    resp2 = query_engine.query(constraint_prompt)
                    cand = extract_sql_from_response(resp2.response)
                    if cand:
                        refined_query = vertical_format_sql(cand)
                except Exception:
                    pass
            locked_list = ", ".join(locked_tables)
            bullet = f"• Tables locked: {locked_list}\n"
            if refined_explanation and not refined_explanation.strip().startswith("•"):
                refined_explanation = bullet + refined_explanation
            else:
                refined_explanation = (refined_explanation or "")

        # Create assistant message
        assistant_message = ChatMessage(
            role="assistant",
            content=f"Here's the SQL query for your request:\n\n```sql\n{refined_query}\n```\n\n**Explanation:**\n{refined_explanation}",
            timestamp=datetime.now(),
            sql_query=refined_query,
            explanation=refined_explanation
        )
        session.messages.append(assistant_message)
        
        # Update session
        session.last_updated = datetime.now()
        save_chat_session(session)
        
        return QueryResponse(
            session_id=session.session_id,
            sql_query=refined_query,
            explanation=refined_explanation,
            message_id=str(uuid.uuid4())
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a chat session."""
    session_file = CHAT_DATA_DIR / f"{session_id}.json"
    if session_file.exists():
        session_file.unlink()
        return {"message": "Session deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Session not found")

# Attempt to include contact router if present
try:
    # Use relative import to avoid picking the root-level contact_backend
    from .contact_backend import router as contact_router
    app.include_router(contact_router)
    print("[OK] Contact router loaded successfully")
except Exception as e:
    print(f"[WARN] Contact router not loaded: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8002)