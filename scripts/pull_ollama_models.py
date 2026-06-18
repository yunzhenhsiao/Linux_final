# scripts/pull_ollama_models.py
import subprocess
import os
import sys

container_name = os.getenv("OLLAMA_CONTAINER_NAME", "transitflow_ollama")
models = ["llama3.2:1b", "nomic-embed-text"]

print(f"Target Ollama Container: {container_name}")
for model in models:
    print(f"Pulling model: {model} inside the container...")
    try:
        # Run docker exec to pull the model
        subprocess.run(["docker", "exec", container_name, "ollama", "pull", model], check=True)
        print(f"Model '{model}' pulled successfully.")
    except Exception as e:
        print(f"Failed to pull model '{model}': {e}")
        print("Please verify if the container is running and Docker is reachable.")
        sys.exit(1)

print("All Ollama models pulled successfully.")
