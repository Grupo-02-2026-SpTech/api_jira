#!/bin/bash

echo "Limpando caches do Python..."

# remover pastas __pycache__
find . -type d -name "__pycache__" -exec rm -rf {} +

# remover arquivos .pyc
find . -type f -name "*.pyc" -delete

echo "Cache limpo com sucesso!"