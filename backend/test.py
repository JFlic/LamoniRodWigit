import requests
import json
from langchain_core.prompts import PromptTemplate

# Set up the base URL for the local Ollama API
url = "http://localhost:11434/api/chat"

data = ""
question = "Who are you?"
print(question)

# Create the prompt template
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

# Format the prompt with the query
formatted_prompt = PROMPT.format(
    context= data,
    input=question
)


# Define the payload with the formatted prompt
payload = {
    "model": "mistral",
    "messages": [{"role": "user", "content": formatted_prompt}]
}

# Send the HTTP POST request with streaming enabled
response = requests.post(url, json=payload)


# Check the response status
if response.status_code == 200:
    for line in response.iter_lines(decode_unicode=True):
        if line:  # Ignore empty lines
            try:
                # Parse each line as a JSON object
                json_data = json.loads(line)
                # Extract and print the assistant's message content
                if "message" in json_data and "content" in json_data["message"]:
                    print(json_data["message"]["content"], end="")
            except json.JSONDecodeError:
                print(f"\nFailed to parse line: {line}")
    print()  # Ensure the final output ends with a newline
else:
    print(f"Error: {response.status_code}")
    print(response.text)