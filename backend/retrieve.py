from fastapi import FastAPI
import time
from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from typing import List, Dict, Any
from pydantic import Field

from VectorTools import VectorDB, truncate_text 

# Connection parameters
CONN_PARAMS = {
    "host": "localhost",
    "port": 5432,
    "database": "postgres",
    "user": "postgres",
    "password": "SweetPotat0!Hug"
}

# Initialize global variables
vector_db = None
llm = None
PROMPT = None

def initialize_components():
    global vector_db, llm, PROMPT
    
    # Initialize vector DB
    vector_db = VectorDB(CONN_PARAMS)

    # Initialize LLM
    llm = Ollama(
        model="mistral",
        base_url="http://localhost:11434",
        temperature=0.5,
        top_p=0.95
    )

    # Define prompt template
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

class SimpleRetriever(BaseRetriever):
    documents: List[Document] = Field(default_factory=list)

    def _get_relevant_documents(self, query: str) -> List[Document]:
        return self.documents

async def process_query(query: str) -> Dict[str, Any]:
    global vector_db, llm, PROMPT
    
    # Initialize components if not already initialized
    if vector_db is None or llm is None or PROMPT is None:
        initialize_components()
    
    try:
        # Perform similarity search
        results = vector_db.similarity_search(query, k=3)
        
        # Extract sources from results to return later
        sources = []
        for result in results:
            source_info = {
                "heading": result['metadata'].get('heading', 'Unknown Title'),
                "source": result['metadata'].get('source', 'None'),
                "url": result['metadata'].get('url',None),
                "page": result['metadata'].get('page', None)
            }
            sources.append(source_info)

        # Convert results to Document objects
        documents = [Document(page_content=result['content'], metadata=result['metadata']) for result in results]

        # Create retrieval and response chain
        question_answer_chain = create_stuff_documents_chain(llm, PROMPT)
        retriever = SimpleRetriever(documents=documents)
        rag_chain = create_retrieval_chain(
            retriever=retriever,
            combine_docs_chain=question_answer_chain
        )
        
        # Get response
        response = rag_chain.invoke({"input": query})

        return {
            "answer": response["answer"],
            "sources": sources
        }
        
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    # Test the query processing
    process_start = time.time()
    
    test_query = "Tell me about City Council"
    result = process_query(test_query)
    # Close connection
    if vector_db:
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
