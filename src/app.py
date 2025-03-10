from fastapi import FastAPI, HTTPException
from orchestrator import handle_query  # orchestrator.py must provide a handle_query(query: str) function

app = FastAPI()

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
    result = handle_query(query_text)
    return {"response": result}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)