from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .orchestrator import OrchestratorAgent

app = FastAPI()
# Add CORS middleware to allow all origins for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

orchestrator = OrchestratorAgent()

@app.post("/query")
async def query(payload: dict):
    """
    Accepts a JSON payload with a "query" key and returns the orchestrator's response.
    Example request payload:
        { "query": "Find bond with ISIN INE001A07QX9" }
    """
    if "query" not in payload:
        raise HTTPException(status_code=400, detail="Missing 'query' in request")
    
    query_text = payload["query"]
    result = orchestrator.process_query(query_text)
    return {"response": result}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)