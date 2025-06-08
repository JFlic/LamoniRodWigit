from fastapi import FastAPI, Response, UploadFile, File, Form, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from Retrieve import process_query
from VectorTools import process_documents, VectorDB
import time
import os
import shutil
from typing import List, Optional
from dotenv import load_dotenv
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()
POSTGRESPASS = os.environ.get("POSTGRESPASS")
SECRET_KEY = os.environ.get("SECRET_KEY", "your-secret-key-here")  # Change this in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# User model
class User(BaseModel):
    email: str
    disabled: Optional[bool] = None

class UserInDB(User):
    hashed_password: str

# Replace this with a real database in production
fake_users_db = {
    "ILoveRod@example.com": {
        "email": "ILoveRod@example.com",
        "hashed_password": pwd_context.hash("ILoveRod"),
        "disabled": False,
    }
}

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_user(db, email: str):
    if email in db:
        user_dict = db[email]
        return UserInDB(**user_dict)

def authenticate_user(fake_db, email: str, password: str):
    user = get_user(fake_db, email)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user(fake_users_db, email)
    if user is None:
        raise credentials_exception
    return user

app = FastAPI()

# Add CORS middleware with expanded configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5501",
        "https://questionroddixon.com",
        "http://localhost:3000",
        "https://lamoni-rod-wigit.vercel.app",
        "https://*.vercel.app",  # Allow all Vercel preview deployments
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "Authorization"],  # Explicitly allow Authorization header
    expose_headers=["*"],
)

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(SCRIPT_DIR, "TempDocumentStore")

# Ensure temp directory exists
os.makedirs(TEMP_DIR, exist_ok=True)

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
            "Access-Control-Allow-Methods": "POST, OPTIONS, GET",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
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

@app.post("/query/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/query/query/upload")
async def upload_files(
    files: List[UploadFile] = File(...),
    category: str = Form(...),
    current_user: User = Depends(get_current_user)
):
    upload_start_time = time.time()
    print(f"\n=== INCOMING FILE UPLOAD ===")
    print(f"Category: {category}")
    print(f"Number of files: {len(files)}")
    
    try:
        # Save uploaded files to temp directory
        saved_files = []
        for file in files:
            print(f"Processing file: {file.filename}")
            # Validate file extension
            if not file.filename.lower().endswith(('.pdf', '.docx', '.md')):
                print(f"Skipping invalid file type: {file.filename}")
                continue
                
            file_path = os.path.join(TEMP_DIR, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            saved_files.append(file_path)
            print(f"Saved file: {file.filename}")

        if not saved_files:
            return {"error": "No valid files were uploaded"}

        # Initialize vector DB
        conn_params = {
            "host": "localhost",
            "port": 5432,
            "database": "postgres",
            "user": "postgres",
            "password": POSTGRESPASS
        }
        vector_db = VectorDB(conn_params)

        # Process documents
        process_start_time = time.time()
        processed_docs = process_documents(TEMP_DIR, category)
        process_end_time = time.time()
        print(f"TIMING: Document processing time: {process_end_time - process_start_time:.4f} seconds")

        # Prepare documents and metadata for vector DB
        documents = []
        metadatas = []
        for doc in processed_docs:
            if hasattr(doc, 'page_content'):
                documents.append(doc.page_content)
            else:
                documents.append(str(doc))
            metadatas.append(doc.metadata)

        # Add to vector DB
        db_start_time = time.time()
        vector_db.add_documents(documents, metadatas)
        db_end_time = time.time()
        print(f"TIMING: Database insertion time: {db_end_time - db_start_time:.4f} seconds")

        # Clean up temp files
        for file_path in saved_files:
            try:
                os.remove(file_path)
            except:
                pass

        upload_end_time = time.time()
        total_time = upload_end_time - upload_start_time
        print(f"TIMING: Total upload processing time: {total_time:.4f} seconds")

        return {
            "message": "Files processed and added to vector database successfully",
            "api_timing": {
                "total_time": f"{total_time:.4f} seconds",
                "processing_time": f"{process_end_time - process_start_time:.4f} seconds",
                "db_insertion_time": f"{db_end_time - db_start_time:.4f} seconds"
            }
        }

    except Exception as e:
        print(f"Error during file upload: {str(e)}")
        # Clean up temp files in case of error
        for file_path in saved_files:
            try:
                os.remove(file_path)
            except:
                pass
        return {"error": str(e)}

# Add this code to run the server when the file is executed directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)