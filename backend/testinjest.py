import os
import glob
import psycopg2
from pathlib import Path
import pandas as pd
from psycopg2.extras import execute_values
import numpy as np
from sentence_transformers import SentenceTransformer
from langchain_docling import DoclingLoader
from docling.chunking import HybridChunker
from langchain_docling.loader import ExportType
from huggingface_hub import login
from langchain_core.documents import Document
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from pymilvus import connections, utility
import time

# Database connection parameters
DB_HOST = "localhost"
DB_NAME = "postgres"  # Your database name
DB_USER = "postgres"         # Your username
DB_PASSWORD = "mysecretpassword"     # Your password
DB_PORT = "5432"             # Default PostgreSQL port

# Embedding parameters
EMBED_MODEL_ID = "BAAI/bge-m3"
EXPORT_TYPE = ExportType.DOC_CHUNKS

# Initialize the embedding model
HF_TOKEN = os.environ.get("HUGGING_FACE_KEY30")
login(HF_TOKEN)
model = SentenceTransformer('all-MiniLM-L6-v2')

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DOC_LOAD_DIR = os.path.join(SCRIPT_DIR, "TempDocumentStore")
CSV_FILE = os.path.join(SCRIPT_DIR, "LamoniUrls.csv")

# Create the chunker for document processing
chunker = HybridChunker(
    tokenizer=EMBED_MODEL_ID,
    max_tokens=2000,
    overlap_tokens=200,
    split_by_paragraph=True,
    min_tokens=50
)

# Sample data - text entries we want to vectorize
sample_texts = [
    "Machine learning is a subfield of artificial intelligence.",
    "Lamoni Iowa as a mail building, it's hours are 5:00am - 9:00pm",
    "Natural language processing deals with interactions between computers and human language.",
    "Vector databases store and retrieve high-dimensional vectors efficiently.",
    "PostgreSQL is an open-source relational database system.",
    "Embeddings capture semantic meaning in numerical vector form."
]

def connect_to_db():
    """Establish connection to PostgreSQL database"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        print("Connected to PostgreSQL database successfully!")
        return conn
    except Exception as e:
        print(f"Error connecting to PostgreSQL database: {e}")
        return None

def setup_tables(conn):
    """Create necessary tables for vector storage if they don't exist"""
    
    cursor = conn.cursor()
    
    # Create extension if it doesn't exist
    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    
    # Create a table with a vector column
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vector_data (
        id SERIAL PRIMARY KEY,
        text TEXT NOT NULL,
        embedding vector(384)  -- Dimension size matches the embedding model
    );
    """)
    
    conn.commit()
    print("Tables set up successfully!")

def create_vector_table(conn):
    """Create the vector table if it doesn't exist"""
    cursor = conn.cursor()
    
    # Create the vector extension if not exists
    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
    
    # Create the table if not exists
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vector_data (
        id SERIAL PRIMARY KEY,
        text TEXT NOT NULL,
        embedding vector(384),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Create index for faster similarity search
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS vector_idx ON vector_data 
    USING ivfflat (embedding vector_cosine_ops) 
    WITH (lists = 100)
    """)
    
    conn.commit()
    print("Vector table created or already exists")

def generate_embeddings(texts):
    """Generate embeddings for the given texts"""
    return model.encode(texts)

def find_url(csv_file, document_name):
    """
    Search for a document name in a CSV file and return the corresponding URL.
    
    Parameters:
    csv_file (str): Path to the CSV file.
    document_name (str): The name of the document to search for.
    
    Returns:
    str: The corresponding URL if found, otherwise None.
    """
    try:
      df = pd.read_csv(csv_file)
      result = df.loc[df.iloc[:, 1] == document_name, df.columns[0]]
      return result.values[0] if not result.empty else None
    except Exception as e:
        print(f"Error: {e}")
        return None

def trim_metadata(docs):
    """Trim metadata to prevent oversize issues"""
    trimmed_docs = []
    for doc in docs:
        # editing meta data to correct title
        source = doc.metadata.get("source")
        title = source.replace("c:\\Users\\RODDIXON\\Desktop\\LamoniRodWigit\\backend\\TempDocumentStore\\","")
        print(title)
        url = find_url(CSV_FILE, title)
        if not url:
            url = "None"
        
        if ".md" in title:
            title = title.replace(".md","")

        if ".docx" in title:
            title = title.replace(".docx","")


        simplified_metadata = {
            "title": title,
            "page": doc.metadata.get("page","1"),
            "source": url,   
            "chunk_id": doc.metadata.get("chunk_id", ""),
        }
        
        # If you need to preserve any special fields from dl_meta, extract just what you need
        if "dl_meta" in doc.metadata and isinstance(doc.metadata["dl_meta"], dict):
            # Extract only essential information from dl_meta if needed
            simplified_metadata["doc_type"] = doc.metadata["dl_meta"].get("doc_type", "")
            
        # Create a new document with the simplified metadata
        trimmed_doc = Document(
            page_content=doc.page_content,
            metadata=simplified_metadata
        )
        trimmed_docs.append(trimmed_doc)
    
    return trimmed_docs

def insert_metadata(conn, documents):
    """Insert document metadata into a separate table"""
    cursor = conn.cursor()
    
    # First create the metadata table if it doesn't exist
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS document_metadata (
        id SERIAL PRIMARY KEY,
        document_id INTEGER REFERENCES vector_data(id),
        source TEXT,
        page INTEGER,
        additional_info JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    
    # Get the last inserted IDs
    cursor.execute("SELECT lastval()")
    last_id = cursor.fetchone()[0]
    start_id = last_id - len(documents) + 1
    
    # Prepare metadata for insertion
    metadata_entries = []
    for i, doc in enumerate(documents):
        doc_id = start_id + i
        source = doc.metadata.get('source', '')
        page = doc.metadata.get('page', 0)
        
        # Filter out specific fields and store the rest as JSON
        exclude_keys = ['source', 'page']
        additional_info = {k: v for k, v in doc.metadata.items() if k not in exclude_keys}
        
        metadata_entries.append((doc_id, source, page, json.dumps(additional_info)))
    
    # Insert metadata
    metadata_query = "INSERT INTO document_metadata (document_id, source, page, additional_info) VALUES %s"
    metadata_template = "(%s, %s, %s, %s::jsonb)"
    
    execute_values(cursor, metadata_query, metadata_entries, metadata_template)
    conn.commit()
    
    print(f"Successfully inserted metadata for {len(documents)} documents")

def chunk_documents(conn):
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
        # Trim metadata to prevent oversize issues
        trimmed_docs = trim_metadata(docs)
        all_splits.extend(trimmed_docs)

    # Process DOCX files
    for file in docx_files:
        print(f"Loading DOCX: {Path(file).name}")
        loader = DoclingLoader(
            file_path=[file],
            export_type=EXPORT_TYPE,
            chunker=chunker,
        )
        docs = loader.load()
        # Trim metadata to prevent oversize issues
        trimmed_docs = trim_metadata(docs)
        all_splits.extend(trimmed_docs)

    # Process PDF files
    for file in pdf_files:
        print(f"Loading PDF: {Path(file).name}")
        loader = DoclingLoader(
            file_path=[file],
            export_type=EXPORT_TYPE,
            chunker=chunker,
        )
        docs = loader.load()
        # Trim metadata to prevent oversize issues
        trimmed_docs = trim_metadata(docs)
        all_splits.extend(trimmed_docs)
    
    print(f"Total document chunks created: {len(all_splits)}")
    
    # Initialize embedding and vector store
    embedding = HuggingFaceEmbeddings(model_name=EMBED_MODEL_ID)

    # Process in smaller batches to avoid oversize issues
    batch_size = 5
    total_docs = len(all_splits)

     # Ensure the table exists
    create_vector_table(conn)

    # Process documents in batches
    for i in range(0, total_docs, batch_size):
        end_idx = min(i + batch_size, total_docs)
        batch = all_splits[i:end_idx]
        print(f"Processing batch {i//batch_size + 1}/{(total_docs + batch_size - 1)//batch_size}: documents {i} to {end_idx-1}")
        
        # Extract text content from documents
        texts = [doc.page_content for doc in batch]
        
        # Generate embeddings for the batch
        batch_embeddings = embedding.embed_documents(texts)
        
        # Insert into SQL database
        insert_vector_data(conn, texts, batch_embeddings)
        
        # Add metadata if needed (optional)
        insert_metadata(conn, batch)

    print("Data ingestion complete. Chunks stored in SQL vector database.")
    return len(all_splits)

def insert_vector_data(conn, texts, embeddings):
    """Insert text data along with their vector embeddings"""
    
    cursor = conn.cursor()
    
    # Prepare data for insertion
    data = [(texts[i], embeddings[i].tolist()) for i in range(len(texts))]
    
    # Insert data
    query = "INSERT INTO vector_data (text, embedding) VALUES %s"
    template = "(%s, %s::vector)"
    
    execute_values(cursor, query, data, template)
    conn.commit()
    
    print(f"Successfully inserted {len(texts)} records with embeddings!")

def query_similar_vectors(conn, query_text, limit=3):
    """Query vectors similar to the embedding of the query text"""
    
    # Generate embedding for the query text
    query_embedding = model.encode(query_text).tolist()
    
    cursor = conn.cursor()
    
    # Query for similar vectors using cosine similarity
    cursor.execute("""
    SELECT text, 1 - (embedding <=> %s::vector) AS cosine_similarity
    FROM vector_data
    ORDER BY cosine_similarity DESC
    LIMIT %s;
    """, (query_embedding, limit))
    
    results = cursor.fetchall()
    return results

def main():
    # Connect to database
    start = time.time()
    conn = connect_to_db()
    if not conn:
        return
    
    # # Set up database tables
    # setup_tables(conn)

    
    # # Generate embeddings for sample texts
    # embeddings = generate_embeddings(sample_texts)
    
    # # Insert data with embeddings
    # insert_vector_data(conn, sample_texts, embeddings)
    
    # # Demonstrate a similarity search
    # query = "Tell me about Lamoni mail hours"
    # print(f"\nSearching for texts similar to: '{query}'")
    # similar_texts = query_similar_vectors(conn, query)
    
    # print("\nResults:")
    # for i, (text, similarity) in enumerate(similar_texts):
    #     print(f"{i+1}. Text: {text}")
    #     print(f"   Similarity score: {similarity:.4f}")

    chunk_documents(conn)
    
    end = time.time()
    elapsed_time = end - start

    days = int(elapsed_time // (24 * 3600))
    elapsed_time %= (24 * 3600)
    hours = int(elapsed_time // 3600)
    elapsed_time %= 3600
    minutes = int(elapsed_time // 60)
    seconds = elapsed_time % 60

    print(f"\nTotal process execution time: {days} days, {hours} hours, {minutes} minutes, and {seconds:.2f} seconds")

    # Close the database connection
    # conn.close()
    # print("\nDatabase connection closed.")

if __name__ == "__main__":
    main()