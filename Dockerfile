FROM ollama/ollama:latest

# Expose the Ollama API port
EXPOSE 11434

# Create a startup script
RUN echo '#!/bin/sh\nollama serve &\nsleep 5\nollama pull mistral:7b-instruct\nwait' > /start.sh && \
    chmod +x /start.sh
