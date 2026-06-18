# scripts/pull_ollama_models.py
import os
import sys
import requests

# Load config or fallback
base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
models = ["llama3.2:1b", "nomic-embed-text"]

print(f"Target Ollama API: {base_url}")
for model in models:
    print(f"Pulling model: {model} via Ollama API...")
    try:
        # Check if model already exists to avoid redundant pull
        try:
            r = requests.get(f"{base_url}/api/tags", timeout=5)
            r.raise_for_status()
            existing_models = [m["name"] for m in r.json().get("models", [])]
        except Exception:
            existing_models = []

        normalized_existing = [m.lower() for m in existing_models]
        model_tag = model if ":" in model else f"{model}:latest"
        
        if model_tag.lower() in normalized_existing or model.lower() in normalized_existing:
            print(f"Model '{model}' already exists. Skipping.")
            continue

        r = requests.post(
            f"{base_url}/api/pull",
            json={"name": model, "stream": False},
            timeout=600  # 10 minutes timeout for model pull
        )
        r.raise_for_status()
        print(f"Model '{model}' pulled successfully via API.")
    except Exception as api_err:
        print(f"API pull failed: {api_err}. Trying fallback using docker exec...")
        
        # Fallback to docker exec if API is not reachable or fails
        import subprocess
        container_name = os.getenv("OLLAMA_CONTAINER_NAME", "transitflow_ollama_dev")
        print(f"Target Ollama Container for fallback: {container_name}")
        try:
            subprocess.run(["docker", "exec", container_name, "ollama", "pull", model], check=True)
            print(f"Model '{model}' pulled successfully via docker exec.")
        except Exception as docker_err:
            print(f"Fallback docker exec also failed: {docker_err}")
            sys.exit(1)

print("All Ollama models pulled successfully.")

