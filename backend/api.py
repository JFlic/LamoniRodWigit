from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from retrieve import get_query_result

app = FastAPI()

# Add CORS middleware with expanded configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5501",
        "https://questionroddixon.com",
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
    print('OPTIONS request received')
    return Response(status_code=200)

@app.post("/query/")
async def my_query_endpoint(query: QueryRequest):
    print(f"\n=== INCOMING QUERY ===")
    print(f"Query: {query.query}")
    return await get_query_result(query)

# Add this code to run the server when the file is executed directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)