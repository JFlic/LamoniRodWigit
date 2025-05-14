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
    start_time = time.time()
    
    # Initialize the model (only done once and cached)
    if not hasattr(get_embedding, "model"):
        model_init_start = time.time()
        # Specifically use the BAAI/bge-m3 model from HuggingFace
        get_embedding.model = SentenceTransformer(EMBED_MODEL_ID)
        
        # Move model to GPU if available
        if torch.cuda.is_available():
            get_embedding.model = get_embedding.model.to(torch.device('cuda'))
        model_init_end = time.time()
        print(f"TIMING: Embedding model initialization took {model_init_end - model_init_start:.4f} seconds")
    
    # Generate embedding
    # The SentenceTransformer library handles tokenization, encoding, and normalization
    encode_start = time.time()
    embedding = get_embedding.model.encode(
        text,
        normalize_embeddings=True,  # Ensure vectors are normalized (important for BGE models)
        convert_to_numpy=True,      # Convert to numpy array for efficiency
        show_progress_bar=True 
    )
    encode_end = time.time()
    print(f"TIMING: Text encoding took {encode_end - encode_start:.4f} seconds")
    
    # Convert to list and return
    end_time = time.time()
    print(f"TIMING: get_embedding took {end_time - start_time:.4f} seconds")
    return embedding.tolist()

class VectorDB:
    def __init__(self, conn_params: Dict[str, Any]):
        """Initialize the vector database with connection parameters."""
        start_time = time.time()
        self.conn_params = conn_params
        self.conn = psycopg2.connect(**conn_params)
        self.setup_database()
        end_time = time.time()
        print(f"TIMING: VectorDB initialization took {end_time - start_time:.4f} seconds")
    
    def setup_database(self):
        """Set up the necessary database tables and extensions."""
        start_time = time.time()
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
        end_time = time.time()
        print(f"TIMING: Database setup took {end_time - start_time:.4f} seconds")
    
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
        start_time = time.time()
        # Get vector embedding
        embed_start = time.time()
        query_embedding = get_embedding(query)
        embed_end = time.time()
        print(f"TIMING: Query embedding generation took {embed_end - embed_start:.4f} seconds")
        
        # Prepare query for keyword search - extract meaningful terms
        keyword_start = time.time()
        keywords = self._extract_keywords(query)
        keyword_end = time.time()
        print(f"TIMING: Keyword extraction took {keyword_end - keyword_start:.4f} seconds")
        
        keyword_clause = ""
        
        if keywords:
            # Create a text search query with weights for keyword matching
            keyword_clause = "ts_rank(to_tsvector('english', content), to_tsquery('english', %s)) * (1 - %s) +"
        
        db_query_start = time.time()
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
            
            sql_exec_start = time.time()
            cursor.execute(sql_query, tuple(params))
            sql_exec_end = time.time()
            print(f"TIMING: SQL execution took {sql_exec_end - sql_exec_start:.4f} seconds")
            
            # First-stage retrieval results
            fetch_start = time.time()
            candidates = []
            for doc_id, content, metadata, score in cursor.fetchall():
                candidates.append({
                    "id": doc_id,
                    "content": content,
                    "metadata": metadata,
                    "score": score
                })
            fetch_end = time.time()
            print(f"TIMING: Result fetching took {fetch_end - fetch_start:.4f} seconds")
        db_query_end = time.time()
        print(f"TIMING: Database query total took {db_query_end - db_query_start:.4f} seconds")
        
        # Perform re-ranking using cross-encoder scoring or more detailed similarity
        rerank_start = time.time()
        reranked_results = self._rerank_results(query, candidates)
        rerank_end = time.time()
        print(f"TIMING: Result re-ranking took {rerank_end - rerank_start:.4f} seconds")
        
        end_time = time.time()
        print(f"TIMING: Total similarity_search function took {end_time - start_time:.4f} seconds")
        
        # Return top-k after re-ranking
        return reranked_results[:k]

    def _extract_keywords(self, query: str) -> str:
        """
        Extract meaningful keywords from the query for text search.
        Returns a formatted string for PostgreSQL ts_query.
        """
        start_time = time.time()
        # Remove stop words and special characters
        stop_words = {"a", "an", "the", "and", "or", "but", "is", "are", "in", "on", "at", "to", "for", "with"}
        words = re.findall(r'\b\w+\b', query.lower())
        
        # Filter out stop words and short terms
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        
        if not keywords:
            end_time = time.time()
            print(f"TIMING: _extract_keywords took {end_time - start_time:.4f} seconds (no keywords found)")
            return ""
        
        # Format for PostgreSQL tsquery (word1 | word2 | word3)
        result = " | ".join(keywords)
        end_time = time.time()
        print(f"TIMING: _extract_keywords took {end_time - start_time:.4f} seconds")
        return result

    def _rerank_results(self, query: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Re-rank the candidate results using a more sophisticated scoring method.
        This could use a cross-encoder or more detailed similarity calculation.
        """
        start_time = time.time()
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
        sorted_results = sorted(candidates, key=lambda x: x.get("final_score", 0), reverse=True)
        end_time = time.time()
        print(f"TIMING: _rerank_results took {end_time - start_time:.4f} seconds")
        return sorted_results

    def get_document_count(self) -> int:
        """Get the total number of documents in the database."""
        with self.conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM documents")
            return cursor.fetchone()[0]

    def close(self):
        """Close the database connection."""
        start_time = time.time()
        if self.conn:
            self.conn.close()
        end_time = time.time()
        print(f"TIMING: Database connection close took {end_time - start_time:.4f} seconds")

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

