import os
import glob
import time
import csv
import pandas as pd

from pathlib import Path
from dotenv import load_dotenv
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from langchain_milvus import Milvus
from pymilvus import connections, utility
from langchain_docling.loader import ExportType
from langchain_docling import DoclingLoader
from docling.chunking import HybridChunker
from langchain_core.documents import Document
from huggingface_hub import login
from huggingface_hub import whoami

# Load environment variables from .env file
load_dotenv()

# Retrieve the token
HF_TOKEN = os.environ.get("HUGGING_FACE_KEY30")
login(HF_TOKEN)

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DOC_LOAD_DIR = os.path.join(SCRIPT_DIR, "TempDocumentStore")
CSV_FILE = os.path.join(SCRIPT_DIR, "LamoniUrls.csv")

# Constants
EMBED_MODEL_ID = "BAAI/bge-m3"
EXPORT_TYPE = ExportType.DOC_CHUNKS
MILVUS_URI = "http://localhost:19530/"

# Create the chunker for document processing
chunker = HybridChunker(
    tokenizer=EMBED_MODEL_ID,
    max_tokens=2000,
    overlap_tokens=200,
    split_by_paragraph=True,
    min_tokens=50
)

# Create output directory if it doesn't exist
os.makedirs(DOC_LOAD_DIR, exist_ok=True)

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
        title = source.replace("TempDocumentStore\\","")

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

    # Establish connection
    connections.connect(alias="default", uri=MILVUS_URI)

    # Check if the collection already exists
    collection_name = "lamoni_collection"
    collection_exists = utility.has_collection(collection_name)

    for i in range(0, total_docs, batch_size):
        end_idx = min(i + batch_size, total_docs)
        batch = all_splits[i:end_idx]
        print(f"Processing batch {i//batch_size + 1}/{(total_docs + batch_size - 1)//batch_size}: documents {i} to {end_idx-1}")
        
        if not collection_exists:
                # Create the collection if it does not exist
                vectorstore = Milvus.from_documents(
                    documents=batch,
                    embedding=embedding,
                    collection_name=collection_name,
                    connection_args={"uri": MILVUS_URI},
                    index_params={"index_type": "FLAT", "metric_type": "COSINE"},
                )
                collection_exists = True  # Set flag to avoid recreating
        else:
            # Connect to the existing collection and add documents
            vectorstore = Milvus(collection_name=collection_name,
                                embedding_function=embedding,
                                connection_args={"uri": MILVUS_URI},
                                auto_id=True,)
            vectorstore.add_documents(batch)

    print("Data ingestion complete. Chunks stored in Milvus.")
    return len(all_splits)

# Main execution
if __name__ == "__main__":
    process_start = time.time()

    # Step 2: Process and ingest the documents
    print("\n=== INGESTING DOCUMENTS ===")
    num_chunks = ingest_documents()
    print(f"Completed ingestion with {num_chunks} chunks created")
    
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