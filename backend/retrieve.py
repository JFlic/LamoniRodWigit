from fastapi import FastAPI
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from pathlib import Path
from langchain_milvus import Milvus
from langchain_community.llms import Ollama
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import PromptTemplate
from langchain_huggingface.embeddings import HuggingFaceEmbeddings

load_dotenv()

env_path = os.path.join(os.path.dirname(__file__), ".env")

# Constants
EMBED_MODEL_ID = "BAAI/bge-m3"
MILVUS_URI = "http://localhost:19530"
TOP_K = 4
OLLAMA_HOST = os.getenv("http://localhost:11434/api/chat")

app = FastAPI()

class QueryRequest(BaseModel):
    query: str

@app.post("/query/")
async def get_query_result(query: QueryRequest):
    # Initialize models and variables
    embedding = HuggingFaceEmbeddings(model_name=EMBED_MODEL_ID)
    vectorstore = Milvus(
        collection_name="lamoni_collection",
        embedding_function=embedding,
        connection_args={"uri": MILVUS_URI},
    )

    retriever = vectorstore.as_retriever(search_kwargs={"k": TOP_K})

    # Initialize Ollama with Mistral
    llm = Ollama(
        model="mistral",
        base_url="http://localhost:11434",
        temperature=0.5,
        top_p=0.95
    )
    
    # Significantly improved prompt with clear formatting instructions
    PROMPT = PromptTemplate.from_template(
        """"role": "You are an AI assistant named Rod Dixon for the town of Lamoni. 
        You can provide information, answer questions and perform other tasks as needed.
        Don't repeat queries." 
        
        \n---------------------\n{context}\n---------------------\n
        
        Given the context information and not prior knowledge, answer the query.
        If the context is empty say that you don't have any information about the question.
        Don't give sources.
        At the end tell the user that if they have anymore questions to let you know.
        Format your response in proper markdown with formatting symbols.
        
        2. Use line breaks between paragraphs (two newlines).
        3. For any lists:
           - Use bullet points with a dash (-) and a space before each item
           - Leave a line break before the first list item
           - Each list item should be on its own line
        4. For numbered lists:
           - Use numbers followed by a period (1. )
           - Leave a line break before the first list item
           - Each numbered item should be on its own line
        5. For section headings, use ## (double hash) with a space after.
        6. Make important terms **bold** using double asterisks.
        7. If you include code blocks, use triple backticks with the language name.
        8. Do not use line breaks within the same paragraph.
        
        \nQuery: {input}\nAnswer:\n"""
    )

    # Create retrieval and response chain
    question_answer_chain = create_stuff_documents_chain(llm, PROMPT)
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)
    resp_dict = rag_chain.invoke({"input": query.query})
    clipped_answer = resp_dict["answer"]

    # Format sources to only include title and page number
    filtered_sources = [
        {
            "title": doc.metadata.get("title", "Unknown"), 
            "page": doc.metadata.get("page", "1"),
            "source": doc.metadata.get("source", "").split("\\")[-1] if doc.metadata.get("source") else "Unknown"
        }
        for doc in resp_dict["context"]
    ]
    print(clipped_answer)
    
    return {
        "question": query.query,
        "answer": clipped_answer,
        "sources": filtered_sources,
    }
