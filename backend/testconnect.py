import psycopg2
import numpy as np
from psycopg2.extras import execute_values
import os
import json
import glob
from pathlib import Path
from typing import List, Dict, Any, Tuple
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv
from huggingface_hub import login
from langchain_docling.loader import ExportType
from langchain_docling import DoclingLoader
from docling.chunking import HybridChunker
from langchain_huggingface.embeddings import HuggingFaceEmbeddings

# Load environment variables from .env file
load_dotenv()

# Retrieve the token
HF_TOKEN = os.environ.get("HUGGING_FACE_KEY30")
login(HF_TOKEN)

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DOC_LOAD_DIR = os.path.join(SCRIPT_DIR, "TempDocumentStore")

# Constants
EMBED_MODEL_ID = "BAAI/bge-m3"
EXPORT_TYPE = ExportType.DOC_CHUNKS

# Create the chunker for document processing
chunker = HybridChunker(
    tokenizer=EMBED_MODEL_ID,
    max_tokens=2000,
    overlap_tokens=200,
    split_by_paragraph=True,
    min_tokens=50
)

def ingest_documents():
    """Process and ingest documents into Milvus"""
    print("Starting document ingestion process...")
    
    # Gather all PDF and Markdown files
    pdf_files = glob.glob(os.path.join(DOC_LOAD_DIR, "*.pdf"))
    md_files = glob.glob(os.path.join(DOC_LOAD_DIR, "*.md"))
    docx_files = glob.glob(os.path.join(DOC_LOAD_DIR, "*.docx"))

    print(f"Processing {len(pdf_files)} PDFs, {len(md_files)} Markdown and {len(docx_files)} DOCX files")

    # Load and chunk documents
    all_splits = []

    # Process Markdown files
    for file in md_files:
        print(f"Loading Markdown: {Path(file).name}")
        loader = DoclingLoader(
            file_path=[file],
            export_type=EXPORT_TYPE,
            chunker=chunker,
        )
        docs = loader.load()

        all_splits.extend(docs)

    # Process DOCX files
    for file in docx_files:
        print(f"Loading DOCX: {Path(file).name}")
        loader = DoclingLoader(
            file_path=[file],
            export_type=EXPORT_TYPE,
            chunker=chunker,
        )
        docs = loader.load()

        all_splits.extend(docs)

    # Process PDF files
    for file in pdf_files:
        print(f"Loading PDF: {Path(file).name}")
        loader = DoclingLoader(
            file_path=[file],
            export_type=EXPORT_TYPE,
            chunker=chunker,
        )
        docs = loader.load()

        all_splits.extend(docs)
    
    print(f"Total document chunks created: {len(all_splits)}")
    print(all_splits)
    
    # Initialize embedding and vector store
    embedding = HuggingFaceEmbeddings(model_name=EMBED_MODEL_ID)

    # Process in smaller batches to avoid oversize issues
    batch_size = 5
    total_docs = len(all_splits)


def get_embedding(text: str) -> List[float]:
    "Generate embedding for text using BAAI/bge-m3"
    print("Starting document embedding process...")
    
    # Gather all PDF and Markdown files
    pdf_files = glob.glob(os.path.join(DOC_LOAD_DIR, "*.pdf"))
    md_files = glob.glob(os.path.join(DOC_LOAD_DIR, "*.md"))
    docx_files = glob.glob(os.path.join(DOC_LOAD_DIR, "*.docx"))

    print(f"Processing {len(pdf_files)} PDFs, {len(md_files)} Markdown and {len(docx_files)} DOCX files")

    # Load and chunk documents
    all_splits = []

    # Process Markdown files
    for file in md_files:
        print(f"Loading Markdown: {Path(file).name}")
        loader = DoclingLoader(
            file_path=[file],
            export_type=EXPORT_TYPE,
            chunker=chunker,
        )
        docs = loader.load()
        
        # Trim metadata for all_splits to prevent oversize issues
        all_splits.extend(docs)

        print(all_splits)

    # Dummy embeddings for illustration
    import hashlib
    # Create a deterministic but random-looking vector based on text hash
    hash_object = hashlib.md5(text.encode())
    seed = int(hash_object.hexdigest(), 16) % 10**8
    np.random.seed(seed)
    return np.random.random(1536).tolist()  # 1536 is OpenAI ada embedding dimension

class VectorDB:
    def __init__(self, conn_params: Dict[str, Any]):
        """Initialize the vector database with connection parameters."""
        self.conn_params = conn_params
        self.conn = psycopg2.connect(**conn_params)
        self.setup_database()
    
    def setup_database(self):
        """Set up the necessary database tables and extensions."""
        with self.conn.cursor() as cursor:
            try:
                # Create pgvector extension if it doesn't exist
                cursor.execute("""
                CREATE EXTENSION IF NOT EXISTS vector;
                """)
                
                # Create documents table if it doesn't exist
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id SERIAL PRIMARY KEY,
                    content TEXT NOT NULL,
                    metadata JSONB,
                    embedding vector(1536)
                );
                """)
                
                # Try to create an index for faster similarity search
                try:
                    cursor.execute("""
                    CREATE INDEX IF NOT EXISTS embedding_idx ON documents 
                    USING ivfflat (embedding vector_l2_ops)
                    WITH (lists = 100);
                    """)
                except Exception as e:
                    print(f"Warning: Could not create IVFFlat index: {e}")
                    print("Creating simple L2 index instead...")
                    cursor.execute("""
                    CREATE INDEX IF NOT EXISTS embedding_idx ON documents 
                    USING btree (embedding);
                    """)
                
                self.conn.commit()
            except Exception as e:
                print(f"Database setup error: {e}")
                print("If the pgvector extension is not available, please install it first.")
                self.conn.rollback()
    
    def add_documents(self, documents: List[str], metadatas: List[Dict] = None):
        """Add documents and their embeddings to the database."""
        if metadatas is None:
            metadatas = [{}] * len(documents)
        
        
        with self.conn.cursor() as cursor:
            for doc, metadata in zip(documents, metadatas):
                embedding = get_embedding(doc)
                # Format the embedding as a PostgreSQL vector using the proper format
                embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
                
                cursor.execute(
                    """
                    INSERT INTO documents (content, metadata, embedding)
                    VALUES (%s, %s, %s::vector)
                    RETURNING id
                    """,
                    (doc, json.dumps(metadata), embedding_str)
                )
            
            self.conn.commit()
    
    def similarity_search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Perform similarity search to find documents similar to the query.
        Returns the top k most similar documents.
        """
        query_embedding = get_embedding(query)
        
        with self.conn.cursor() as cursor:
            # Format the query embedding as a PostgreSQL vector
            query_embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
            
            cursor.execute(
                """
                SELECT id, content, metadata, 
                       1 - (embedding <-> %s::vector) as similarity
                FROM documents
                ORDER BY embedding <-> %s::vector
                LIMIT %s
                """,
                (query_embedding_str, query_embedding_str, k)
            )
            
            results = []
            for doc_id, content, metadata, similarity in cursor.fetchall():
                results.append({
                    "id": doc_id,
                    "content": content,
                    "metadata": metadata,
                    "similarity": similarity
                })
            
            return results

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()

if __name__ == "__main__":
    # Connection parameters
    conn_params = {
        "host": "localhost",  # For local Python script connecting to Docker container
        "port": 5432,
        "database": "postgres",
        "user": "postgres",
        "password": "SweetPotat0!Hug"
    }
    
    # Initialize vector DB
    vector_db = VectorDB(conn_params)
    
    # Example documents
    documents = [
        "The quick brown fox jumps over the lazy dog",
        "Machine learning is a subset of artificial intelligence",
        "Neural networks are inspired by the human brain",
        "PostgreSQL is an advanced open-source database",
        "Vector search enables semantic search capabilities"
    ]
    
    # Example metadata
    metadatas = [
        {"source": "example1", "category": "phrase"},
        {"source": "example2", "category": "AI"},
        {"source": "example3", "category": "AI"},
        {"source": "example4", "category": "database"},
        {"source": "example5", "category": "search"}
    ]
    
    # Add documents to vector DB
    vector_db.add_documents(documents, metadatas)
    
    # Perform a query
    query = "AI"
    results = vector_db.similarity_search(query, k=3)
    
    print(f"Query: {query}\n")
    print("Top 3 results:")
    for i, result in enumerate(results):
        print(f"{i+1}. {result['content']} (Similarity: {result['similarity']:.4f})")
        print(f"   Metadata: {result['metadata']}")
    
    # Close connection
    vector_db.close()