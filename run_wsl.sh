#!/bin/bash
# Run MVP RAG Local inside WSL2

cd /mnt/c/www/mvp-rag-local

# Create venv if not exists
if [ ! -d "venv_wsl" ]; then
    python3 -m venv venv_wsl
    ./venv_wsl/bin/pip install --upgrade pip
    ./venv_wsl/bin/pip install -r requirements.txt
fi

# Export environment
export POSTGRES_HOST=localhost
export QDRANT_HOST=localhost

# Run Streamlit
./venv_wsl/bin/streamlit run app.py --server.headless true --server.port 8501
