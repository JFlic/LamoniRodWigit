import psycopg2
import numpy as np

# Connect to PostgreSQL
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="vectortest",
    user="postgres",
    password="mysecretpassword"
)
cursor = conn.cursor()

# Verify the vector extension is available
cursor.execute("SELECT extname FROM pg_extension WHERE extname = 'vector'")
result = cursor.fetchone()
print(f"Vector extension installed: {result is not None}")

# Create a table for embeddings if it doesn't exist
cursor.execute("""
CREATE TABLE IF NOT EXISTS embeddings (
    id serial PRIMARY KEY,
    content text,
    embedding vector(3)
);
""")
conn.commit()

# Generate some fake embeddings (normally these would come from your model)
def generate_fake_embedding(dim=3):
    return np.random.rand(dim).tolist()

# Insert some test documents with embeddings
test_docs = [
    {"content": "This is a test document about artificial intelligence.", "embedding": generate_fake_embedding()},
    {"content": "Vectors are mathematical objects with magnitude and direction.", "embedding": generate_fake_embedding()},
    {"content": "PostgreSQL is an advanced open-source database.", "embedding": generate_fake_embedding()}
]

# Insert the documents - Format embeddings correctly for pgvector
for doc in test_docs:
    # Format the embedding as a string with square brackets for pgvector
    embedding_str = f"[{','.join(str(x) for x in doc['embedding'])}]"
    cursor.execute(
        "INSERT INTO embeddings (content, embedding) VALUES (%s, %s)",
        (doc["content"], embedding_str)
    )
conn.commit()

# Query to verify data was inserted
cursor.execute("SELECT COUNT(*) FROM embeddings")
count = cursor.fetchone()[0]
print(f"Number of embeddings in database: {count}")

# Test a simple vector search
# Format the query embedding correctly for pgvector
query_embedding = test_docs[0]["embedding"]
query_embedding_str = f"[{','.join(str(x) for x in query_embedding)}]"

cursor.execute("""
SELECT id, content, embedding <-> %s AS distance
FROM embeddings
ORDER BY distance
LIMIT 3
""", (query_embedding_str,))

results = cursor.fetchall()
print("\nMost similar documents:")
for result in results:
    print(f"ID: {result[0]}, Distance: {result[2]}, Content: {result[1][:50]}...")

conn.close()
print("\nTest completed successfully!")