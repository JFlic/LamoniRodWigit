import psycopg2
import numpy as np
import pandas as pd
from psycopg2.extras import execute_values
import os
import re
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
from sentence_transformers import SentenceTransformer
import torch
import datetime
import time

# Load environment variables from .env file
load_dotenv()
POSTGRESPASS = os.environ.get("POSTGRESPASS")

process_start = time.time()

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DOC_LOAD_DIR = os.path.join(SCRIPT_DIR, "TempDocumentStore")
CSV_FILE = os.path.join(SCRIPT_DIR, "LamoniUrls.csv")

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

def find_url(csv_file, document_name):
    """
    Search for a document name in a CSV file and return the corresponding URL.
    
    Parameters:
    csv_file (str): Path to the CSV file.
    document_name (str): The name of the document to search for.
    
    Returns:
    str: The corresponding URL if found, otherwise None.
    """

    document_name = document_name.replace("c:\\Users\\RODDIXON\\Desktop\\LamoniRodWigit\\backend\\","")


    try:
      df = pd.read_csv(csv_file)
      result = df.loc[df.iloc[:, 1] == document_name, df.columns[0]]
      return result.values[0] if not result.empty else None
    except Exception as e:
        print(f"Error: {e}")
        return None

def process_documents(urlpath, category):
    """Process and ingest documents into PGvectorstore"""
    print("Starting document ingestion process...")
    
    # Gather all PDF and Markdown files
    pdf_files = glob.glob(os.path.join(urlpath, "*.pdf"))
    md_files = glob.glob(os.path.join(urlpath, "*.md"))
    docx_files = glob.glob(os.path.join(urlpath, "*.docx"))

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

        for doc in docs:
            # Extract only what we need from the original metadata
            source_file = None
            headings = None
            timestamp = datetime.datetime.now().isoformat()
            
            if hasattr(doc, 'metadata') and doc.metadata:
                if 'source' in doc.metadata:
                    source_file = doc.metadata['source']
                
                if 'dl_meta' in doc.metadata and 'headings' in doc.metadata['dl_meta']:
                    headings = doc.metadata['dl_meta']['headings'][0] if doc.metadata['dl_meta']['headings'] else None
            
                source_file = source_file.replace(f"c:\\Users\\RODDIXON\\Desktop\\LamoniRodWigit\\backend\\TempDocumentStore\\","")
                url = find_url(CSV_FILE,source_file)

                
            # Replace the metadata with simplified version
            doc.metadata = {
                'source': source_file,
                'heading': headings,
                'scraped_at': timestamp,
                "url": url,
                "type": category
            }

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

        for doc in docs:
            # Extract only what we need from the original metadata
            source_file = None
            headings = None
            timestamp = datetime.datetime.now().isoformat()
            
            if hasattr(doc, 'metadata') and doc.metadata:
                if 'source' in doc.metadata:
                    source_file = doc.metadata['source']
                
                if 'dl_meta' in doc.metadata and 'headings' in doc.metadata['dl_meta']:
                    headings = doc.metadata['dl_meta']['headings'][0] if doc.metadata['dl_meta']['headings'] else None
            
                source_file = source_file.replace(f"c:\\Users\\RODDIXON\\Desktop\\LamoniRodWigit\\backend\\TempDocumentStore\\","")
                url = find_url(CSV_FILE,source_file)

                
            # Replace the metadata with simplified version
            doc.metadata = {
                'source': source_file,
                'heading': headings,
                'scraped_at': timestamp,
                "url": url,
                "type": category
            }

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

        for doc in docs:
            # Extract only what we need from the original metadata
            source_file = None
            headings = None
            timestamp = datetime.datetime.now().isoformat()
            
            if hasattr(doc, 'metadata') and doc.metadata:
                if 'source' in doc.metadata:
                    source_file = doc.metadata['source']
                
                if 'dl_meta' in doc.metadata and 'headings' in doc.metadata['dl_meta']:
                    headings = doc.metadata['dl_meta']['headings'][0] if doc.metadata['dl_meta']['headings'] else None
            
                source_file = source_file.replace(f"c:\\Users\\RODDIXON\\Desktop\\LamoniRodWigit\\backend\\TempDocumentStore\\","")
                url = find_url(CSV_FILE,source_file)

                
            # Replace the metadata with simplified version
            doc.metadata = {
                'source': source_file,
                'heading': headings,
                'scraped_at': timestamp,
                "url": url,
                "type": category
            }
 
        all_splits.extend(docs)
    
    print(f"Total document chunks created: {len(all_splits)}")

    return all_splits

def get_embedding(text: str) -> List[float]:
    "Generate embedding for text using BAAI/bge-m3"
    print("Starting document embedding process...")
    
    # Initialize the model (only done once and cached)
    if not hasattr(get_embedding, "model"):
        # Specifically use the BAAI/bge-m3 model from HuggingFace
        get_embedding.model = SentenceTransformer(EMBED_MODEL_ID)
        
        # Move model to GPU if available
        if torch.cuda.is_available():
            get_embedding.model = get_embedding.model.to(torch.device('cuda'))
    
    # Generate embedding
    # The SentenceTransformer library handles tokenization, encoding, and normalization
    embedding = get_embedding.model.encode(
        text,
        normalize_embeddings=True,  # Ensure vectors are normalized (important for BGE models)
        convert_to_numpy=True,      # Convert to numpy array for efficiency
        show_progress_bar=True 
    )
    
    # Convert to list and return
    return embedding.tolist()

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
                    embedding vector(1024)
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
    
    def similarity_search(self, query: str, k: int = 5, hybrid_ratio: float = 0.5) -> List[Dict[str, Any]]:
        """
        Perform hybrid similarity search (vector + BM25-like) to find documents similar to the query.
        Returns the top k most similar documents after re-ranking.
        
        Args:
            query: The query string
            k: The number of results to return
            hybrid_ratio: Balance between vector and keyword search (0.0 = all keyword, 1.0 = all vector)
        """
        # Get vector embedding
        query_embedding = get_embedding(query)
        
        # Prepare query for keyword search - extract meaningful terms
        keywords = self._extract_keywords(query)
        keyword_clause = ""
        
        if keywords:
            # Create a text search query with weights for keyword matching
            keyword_clause = "ts_rank(to_tsvector('english', content), to_tsquery('english', %s)) * (1 - %s) +"
        
        with self.conn.cursor() as cursor:
            # Format the query embedding as a PostgreSQL vector
            query_embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
            
            sql_query = f"""
            SELECT id, content, metadata, 
                {keyword_clause if keywords else ""} (1 - (embedding <=> %s::vector)) * %s as hybrid_score
            FROM documents
            WHERE 1=1
            """
            
            # Add keyword filter for first-stage retrieval if we have keywords
            # This helps narrow down candidates before vector similarity
            if keywords:
                sql_query += " AND to_tsvector('english', content) @@ to_tsquery('english', %s)"
                
            sql_query += """
            ORDER BY hybrid_score DESC
            LIMIT %s * 3
            """
            
            # Prepare parameters
            params = []
            if keywords:
                params.extend([keywords, hybrid_ratio])
            params.extend([query_embedding_str, hybrid_ratio if keywords else 1.0])
            if keywords:
                params.append(keywords)
            params.append(k)
            
            cursor.execute(sql_query, tuple(params))
            
            # First-stage retrieval results
            candidates = []
            for doc_id, content, metadata, score in cursor.fetchall():
                print(metadata)
                print(score)
                candidates.append({
                    "id": doc_id,
                    "content": content,
                    "metadata": metadata,
                    "score": score
                })
            
            # Perform re-ranking using cross-encoder scoring or more detailed similarity
            reranked_results = self._rerank_results(query, candidates)
            
            # Return top-k after re-ranking
            return reranked_results[:k]

    def _extract_keywords(self, query: str) -> str:
        """
        Extract meaningful keywords from the query for text search.
        Returns a formatted string for PostgreSQL ts_query.
        """
        # Remove stop words and special characters
        stop_words = {"a", "an", "the", "and", "or", "but", "is", "are", "in", "on", "at", "to", "for", "with"}
        words = re.findall(r'\b\w+\b', query.lower())
        
        # Filter out stop words and short terms
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        
        if not keywords:
            return ""
        
        # Format for PostgreSQL tsquery (word1 | word2 | word3)
        return " | ".join(keywords)

    def _rerank_results(self, query: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Re-rank the candidate results using a more sophisticated scoring method.
        This could use a cross-encoder or more detailed similarity calculation.
        """
        # For BAAI/bge-m3, ideally you would use a cross-encoder here
        # But as a simple implementation, we can use a combination of:
        # 1. Exact phrase match bonus
        # 2. Keyword density
        # 3. Original hybrid score
        
        for doc in candidates:
            content = doc["content"].lower()
            query_lower = query.lower()
            
            # Exact phrase match bonus (1.5x boost if exact query appears)
            exact_match_bonus = 1.5 if query_lower in content else 1.0
            
            # Keyword density check
            keywords = self._extract_keywords(query).split(" | ")
            keyword_count = sum(1 for keyword in keywords if keyword in content)
            keyword_density = keyword_count / len(keywords) if keywords else 0
            
            # Compute final score - original score plus bonuses
            final_score = doc["score"] * exact_match_bonus * (1 + keyword_density * 0.5)
            doc["final_score"] = final_score
        
        # Sort by final score
        return sorted(candidates, key=lambda x: x.get("final_score", 0), reverse=True)

    def get_document_count(self) -> int:
        """Get the total number of documents in the database."""
        with self.conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM documents")
            return cursor.fetchone()[0]

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()

def truncate_text(text, max_length=100):
    """
    Truncate text to the specified maximum length and add ellipsis if needed.
    
    Args:
        text: The text to truncate
        max_length: Maximum length of the output text
        
    Returns:
        Truncated text with ellipsis if necessary
    """
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

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
    
    # # Check initial document count
    # initial_count = vector_db.get_document_count()
    # print(f"Initial document count: {initial_count}")
    
    # # Retreive data from TempDocumentStore
    processed_docs = process_documents(DOC_LOAD_DIR)

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
    
    # Perform a query
    query = "who are you?"
    results = vector_db.similarity_search(query, k=3)
    
    print(f"\nQuery: {query}\n")
    print("Top 3 results:")
    if not results:
        print("No results found!")
    else:
        for i, result in enumerate(results):
            print(f"{i+1}. {truncate_text(result['content'])}")
            print(f"   Metadata: {result['metadata']}")
    
    # Close connection
    vector_db.close()

# End Time
process_end = time.time()
elapsed_time = process_end - process_start

# Convert to days, hours, minutes, and seconds
days = int(elapsed_time // (24 * 3600))
elapsed_time %= (24 * 3600)
hours = int(elapsed_time // 3600)
elapsed_time %= 3600
minutes = int(elapsed_time // 60)
seconds = elapsed_time % 60

print(f"\nTotal process execution time: {days} days, {hours} hours, {minutes} minutes, and {seconds:.2f} seconds")
