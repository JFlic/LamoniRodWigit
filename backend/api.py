from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from Retrieve import process_query
import time

app = FastAPI()

# Add CORS middleware with expanded configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5501",
        "https://questionroddixon.com",
        "http://localhost:3000",
        "https://lamoni-rod-wigit.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str

@app.get("/")
async def root():
    return {"message": "Welcome to the API"}

@app.options("/query/")
async def options_query():
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "https://lamoni-rod-wigit.vercel.app",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Max-Age": "3600",
        }
    )

@app.post("/query/")
async def my_query_endpoint(query: QueryRequest):
    total_start_time = time.time()
    print(f"\n=== INCOMING QUERY ===")
    print(f"Query: {query.query}")
    
    # Process the query
    process_start_time = time.time()
    result = await process_query(query.query)
    process_end_time = time.time()
    process_time = process_end_time - process_start_time
    print(f"TIMING: Query processing total time: {process_time:.4f} seconds")
    
    # Calculate response preparation time
    response_prep_start = time.time()
    # Add timing data to result
    result["api_timing"] = {
        "process_time": f"{process_time:.4f} seconds"
    }
    response_prep_end = time.time()
    print(f"TIMING: Response preparation time: {response_prep_end - response_prep_start:.4f} seconds")
    
    # Calculate total API time
    total_end_time = time.time()
    total_time = total_end_time - total_start_time
    print(f"TIMING: Total API endpoint time: {total_time:.4f} seconds")
    result["api_timing"]["total_time"] = f"{total_time:.4f} seconds"
    
    return result

# Add this code to run the server when the file is executed directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)