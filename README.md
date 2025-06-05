# Small Town RAG AI model
This is a small town RAG AI solution for the Town of Lamoni Iowa called Rod Dixon. Rod can tell you anything from facebook posts that are happening in the Town to historical data from over 100 years ago

# backend
The backend contains the vector storage, webscrape, retrieval and api scripts as well as some prototype pipelines that I experimented with.
Currently the RAG model works with cosine similarity search and re-rank. The embedding model for the search functionality is BAAI/bge-m3. The LLM model that was used was qwen3:1.7b. Using bigger models with more parameters did give better results but qwen3:1.7b seemed to be the best mix of speed and results for my hardware setup.


# frontend
There are two "frontends" for Rod one which is a widget that sits on the LeadonLamoni.com website and another that is located in the frontend folder that's a dedicated webpage designed to look like AI chat websites. 


# Here's some stuff that Rod should know for Lamoni

120 years of newspaper via the Lamoni Chronical
Local attractions and points of interest
Events happening around Lamoni
Recommendations for restaurants, shops, and services
General information about Lamoni
Anything on the Graceland University Website
Anything on the LeadOnLamoni Website
