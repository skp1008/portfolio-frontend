"""
rag_code.py

Enhanced RAG system that builds a vector index from:
  • Historical SQL scripts (with IMPORTANT folder getting 3x weight)
  • Database schema from JSON files
  • Optimized for SQL query generation

Run:
    python rag_code.py
"""

import json
import os
from pathlib import Path
from llama_index.core import VectorStoreIndex, StorageContext, Settings
from llama_index.core.readers import SimpleDirectoryReader
from llama_index.core.schema import Document
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

def load_schema_documents():
    """Load schema from JSON files - create concise table summaries."""
    schema_docs = []
    schema_dir = Path("Schema")
    
    if not schema_dir.exists():
        print("⚠️  Warning: Schema directory not found")
        return schema_docs
    
    # Load each schema file and create one summary document per file
    for schema_file in schema_dir.glob("*.json"):
        try:
            print(f"📖 Loading schema from {schema_file.name}...")
            with open(schema_file, 'r', encoding='utf-8') as f:
                schema_data = json.load(f)
            
            # Create a concise summary of all tables in the schema file
            system_name = schema_file.stem.replace('_schema', '').upper()
            schema_text = f"DATABASE SCHEMA - {system_name} SYSTEM\n\n"
            
            for table_name, columns in schema_data.items():
                schema_text += f"Table: {table_name}\n"
                
                # Only include essential columns (first 5 + key columns)
                essential_cols = []
                key_columns = [col for col in columns if any(key in col.get('column', '').lower() 
                              for key in ['id', 'number', 'account', 'folio', 'date', 'amount', 'reference'])]
                
                # Take first 3 key columns + first 2 other columns
                for col in key_columns[:3]:
                    essential_cols.append(col)
                
                other_cols = [col for col in columns if col not in essential_cols]
                for col in other_cols[:2]:
                    essential_cols.append(col)
                
                for col in essential_cols:
                    col_name = col.get('column', '')
                    col_type = col.get('type', '').split('(')[0]  # Remove size info
                    col_desc = col.get('description', '')[:50]  # Truncate description
                    if col_desc and not col_desc.endswith('.'):
                        col_desc = col_desc.split('.')[0] + '...'
                    schema_text += f"  • {col_name} ({col_type}): {col_desc}\n"
                
                if len(columns) > 5:
                    schema_text += f"  ... and {len(columns) - len(essential_cols)} more columns\n"
                schema_text += "\n"
            
            # Create single document for entire schema file
            doc = Document(
                text=schema_text,
                metadata={
                    "source": "schema",
                    "type": "database_schema",
                    "system": system_name,
                    "schema_file": schema_file.name,
                    "priority": "high"
                }
            )
            schema_docs.append(doc)
                
        except Exception as e:
            print(f"⚠️  Warning: Could not load {schema_file}: {e}")
    
    print(f"✅ Loaded {len(schema_docs)} schema documents (concise summaries)")
    return schema_docs

def load_historical_scripts():
    """Load SQL scripts - prioritize IMPORTANT folder but avoid excessive duplication."""
    all_docs = []
    
    # Load IMPORTANT folder first (high priority) - NO MULTIPLICATION
    important_dir = Path("Historical_Scripts/IMPORTANT")
    if important_dir.exists():
        try:
            print("📖 Loading IMPORTANT scripts...")
            important_docs = SimpleDirectoryReader(str(important_dir)).load_data()
            
            for doc in important_docs:
                # Clean and truncate document text to reduce token usage
                text = doc.text.strip()
                # Keep only first 1000 characters of very long documents
                if len(text) > 1000:
                    text = text[:1000] + "\n... [truncated for efficiency]"
                
                doc_clean = Document(
                    text=text,
                    metadata={
                        "source": "script",
                        "type": "sql_example", 
                        "priority": "high",
                        "category": "important",
                        "file_name": Path(doc.metadata.get('file_path', '')).name
                    }
                )
                all_docs.append(doc_clean)
            print(f"✅ Loaded {len(important_docs)} IMPORTANT documents")
            
        except Exception as e:
            print(f"⚠️  Warning: Could not load IMPORTANT scripts: {e}")
    
    # Load other folders (normal priority) - SAMPLE ONLY
    try:
        print("📖 Loading sample of other historical scripts...")
        other_docs = SimpleDirectoryReader("Historical_Scripts", recursive=True).load_data()
        
        # Filter out IMPORTANT folder and take only a sample
        filtered_docs = []
        for doc in other_docs:
            if "IMPORTANT" not in doc.metadata.get('file_path', ''):
                # Clean and truncate
                text = doc.text.strip()
                if len(text) > 800:  # Smaller limit for non-important docs
                    text = text[:800] + "\n... [truncated]"
                
                doc_clean = Document(
                    text=text,
                    metadata={
                        "source": "script",
                        "type": "sql_example",
                        "priority": "normal",
                        "category": Path(doc.metadata.get('file_path', '')).parent.name,
                        "file_name": Path(doc.metadata.get('file_path', '')).name
                    }
                )
                filtered_docs.append(doc_clean)
                
                # Limit total other documents to prevent token explosion
                if len(filtered_docs) >= 15:  # Max 15 non-important documents
                    break
        
        all_docs.extend(filtered_docs)
        print(f"✅ Loaded {len(filtered_docs)} other script documents (sampled)")
        
    except Exception as e:
        print(f"⚠️  Warning: Could not load other historical scripts: {e}")
    
    return all_docs

def load_documents() -> list:
    """Load all documents for RAG index."""
    all_docs = []
    
    # Load schema documents
    schema_docs = load_schema_documents()
    all_docs.extend(schema_docs)
    
    # Load historical scripts
    script_docs = load_historical_scripts()
    all_docs.extend(script_docs)
    
    if not all_docs:
        raise ValueError("No documents were loaded! Please check your folder structure.")
    
    print(f"\n📊 Total documents loaded: {len(all_docs)}")
    print(f"   • Schema documents: {len(schema_docs)}")
    print(f"   • Script documents: {len(script_docs)}")
    
    return all_docs

def main() -> None:
    print("🔍 Loading documents...")
    docs = load_documents()
    
    print("🔧 Setting up embedding model...")
    
    # Embedding model is fully local; no API key needed.
    embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")

    # Use the new Settings approach instead of deprecated ServiceContext
    Settings.embed_model = embed_model
    Settings.chunk_size = 512  # Smaller chunks for better token management
    Settings.chunk_overlap = 50  # Minimal overlap

    print("🏗️  Building enhanced vector index (this may take a few minutes on first run)...")
    index = VectorStoreIndex.from_documents(
        docs, show_progress=True
    )

    persist_dir = "rag_storage"
    Path(persist_dir).mkdir(exist_ok=True)
    index.storage_context.persist(persist_dir=persist_dir)
    print(f"✅ Enhanced index written to {persist_dir}")
    print("🎉 Enhanced RAG index built successfully!")
    print("💡 Features:")
    print("   • Schema integration for better table understanding")
    print("   • IMPORTANT folder gets 3x weight for priority queries")
    print("   • Optimized for SQL generation")
    print("💡 You can now run: python llm_app.py")

if __name__ == "__main__":
    main()

