import os
from dotenv import load_dotenv
from docling.chunking import HybridChunker
from VectorTools import VectorDB, process_documents

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DOC_LOAD_DIR = os.path.join(SCRIPT_DIR, "TempDocumentStore")

# Constants
EMBED_MODEL_ID = "BAAI/bge-m3"

# Load environment variables from .env file
load_dotenv()
POSTGRESPASS = os.environ.get("POSTGRESPASS")

# Create the chunker for document processing
chunker = HybridChunker(
    tokenizer=EMBED_MODEL_ID,
    max_tokens=2000,
    overlap_tokens=200,
    split_by_paragraph=True,
    min_tokens=50
)

if __name__ == "__main__":

    # Connection parameters
    conn_params = {
        "host": "localhost",  # For local Python script connecting to Docker container
        "port": 5432,
        "database": "postgres",
        "user": "postgres",
        "password": POSTGRESPASS
    }

    # Initialize vector DB
    vector_db = VectorDB(conn_params)

    # Check final document count
    starting_count = vector_db.get_document_count()
    print(f"Starting document count: {starting_count}")

    category = input("What is the category of this data?/nEnter:")

    processed_docs = process_documents(DOC_LOAD_DIR, category)

    documents = []
    metadatas = []

    for doc in processed_docs:
        # Extract the document content
        if hasattr(doc, 'page_content'):
            documents.append(doc.page_content)
        else:
            # Fall back to string representation if no page_content attribute
            documents.append(str(doc))
        
        # Use the trimmed metadata we created
        metadatas.append(doc.metadata)
    
    print(f"Prepared {len(documents)} documents for vector DB")
    
    # Add documents to vector DB
    vector_db.add_documents(documents, metadatas)

    # Check final document count
    final_count = vector_db.get_document_count()
    print(f"Final document count: {final_count}")
