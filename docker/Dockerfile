FROM ubuntu:22.04 

# Install dependencies
RUN apt-get update && apt-get install -y curl

# Install Pixi
RUN curl -fsSL https://pixi.sh/install.sh | bash
ENV PATH="/root/.pixi/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy project files
COPY pixi.toml /app/pixi.toml
COPY pixi.lock /app/pixi.lock
COPY src/ /app/src/
COPY env/ /app/env/
COPY data/ /app/data/

# Create empty dirs if they don't exist
RUN mkdir -p /app/logs

# Install dependencies
RUN pixi install

# Expose the port your FastAPI app uses
EXPOSE 8000

# Health check for FastAPI
HEALTHCHECK CMD curl --fail http://localhost:8000/docs

# Start the FastAPI app directly with uvicorn
ENTRYPOINT ["pixi", "run", "start"]