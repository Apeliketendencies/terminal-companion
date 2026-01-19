#!/bin/bash

# Setup script for Terminal AI Agent

echo "Starting setup for Terminal AI Agent..."

# 1. Install Python dependencies
if [ -f "requirements.txt" ]; then
    echo "Installing requirements..."
    pip install -r requirements.txt
else
    echo "Error: requirements.txt not found."
    exit 1
fi

# 2. Check for Ollama
if ! command -v ollama &> /dev/null; then
    echo "Warning: ollama command not found. Please install Ollama from https://ollama.com/"
else
    echo "Ollama is installed. Pulling model dolphin-mistral:7b..."
    ollama pull dolphin-mistral:7b
fi

# 3. Create a symlink in ~/.local/bin if it exists, otherwise suggest an alias
SCRIPT_PATH="$(realpath agent.py)"
LOCAL_BIN="$HOME/.local/bin"

if [ -d "$LOCAL_BIN" ]; then
    echo "Creating symlink in $LOCAL_BIN..."
    ln -sf "$SCRIPT_PATH" "$LOCAL_BIN/agent"
    echo "Setup complete! You can now run 'agent' from anywhere (after restarting your shell or sourcing your config)."
else
    echo "Adding alias to .zshrc..."
    if ! grep -q "alias agent=" ~/.zshrc; then
        echo "alias agent='$SCRIPT_PATH'" >> ~/.zshrc
        echo "Alias added to .zshrc. Please run 'source ~/.zshrc' to start using 'agent'."
    else
        echo "Alias already exists in .zshrc."
    fi
fi

echo "Done!"
