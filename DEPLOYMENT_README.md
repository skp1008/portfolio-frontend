# SQL Query Generator - Railway Deployment

This document explains how the SQL Query Generator is deployed on Railway and how the RAG system is automatically set up during deployment.

## 🚀 Deployment Process

### 1. Automatic Setup During Deployment

When the application is deployed to Railway, the following happens automatically:

1. **Directory Setup**: Creates necessary directories (`chatbot_data`, `SQL_App/rag_storage`, `frontend`)
2. **RAG File Copying**: Copies the entire `SQL_App` directory from the parent repository
3. **RAG Index Building**: Runs `rag_code.py` to build the vector index from:
   - Database schema files
   - Historical SQL scripts (with IMPORTANT folder getting priority)
4. **Backend Initialization**: Starts the FastAPI server with the built RAG index

### 2. Key Files

- **`setup_deployment.py`**: Main deployment setup script that runs during Railway deployment
- **`llm_chatbot_backend.py`**: FastAPI backend that serves the SQL Query Generator
- **`Procfile`**: Tells Railway to run the setup script before starting the server
- **`requirements.txt`**: All necessary Python dependencies

### 3. Environment Variables Required

- `TOGETHER_API_KEY`: Your Together AI API key for LLM inference

### 4. Health Check

The application provides a `/health` endpoint that returns:

```json
{
  "status": "healthy",
  "service": "sql_chatbot_backend",
  "llama_index_available": true,
  "query_engine_initialized": true,
  "api_key_present": true,
  "rag_storage_path": "/path/to/rag/storage",
  "rag_files_exist": true,
  "chat_data_exists": true,
  "frontend_dir": "/path/to/frontend",
  "deployment_ready": true
}
```

### 5. How It Works

1. **User asks a question** → Frontend sends to `/query` endpoint
2. **RAG retrieval** → System finds relevant schema and SQL examples
3. **LLM generation** → Together AI generates SQL query
4. **Validation** → Query is validated and refined
5. **Response** → User gets SQL query and explanation

### 6. Testing Locally

To test the deployment setup locally:

```bash
cd deploy_stuff
python test_deployment.py
```

This will:
- Run the deployment setup
- Verify all files are created
- Test backend initialization
- Confirm everything works before deploying

### 7. Troubleshooting

**If the app doesn't work after deployment:**

1. Check the Railway logs for any errors during setup
2. Verify `TOGETHER_API_KEY` is set in Railway environment variables
3. Check the `/health` endpoint to see what's missing
4. The setup script will automatically retry RAG building if needed

**Common Issues:**
- RAG storage not found → Setup script will rebuild it
- API key missing → Add `TOGETHER_API_KEY` to Railway environment
- Dependencies missing → Check `requirements.txt` is complete

### 8. File Structure After Deployment

```
deploy_stuff/
├── SQL_App/
│   ├── rag_storage/          # Built during deployment
│   │   ├── docstore.json
│   │   ├── index_store.json
│   │   └── default__vector_store.json
│   ├── rag_code.py           # Copied from parent
│   ├── Schema/               # Copied from parent
│   └── Historical_Scripts/   # Copied from parent
├── chatbot_data/             # Created during deployment
├── frontend/                 # HTML files
├── llm_chatbot_backend.py   # Main backend
├── setup_deployment.py       # Deployment script
└── Procfile                 # Railway configuration
```

The deployment ensures that users can immediately start using the SQL Query Generator without any manual setup - the RAG index is built automatically during the first deployment.
