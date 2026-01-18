# Terminal AI Agent

A powerful terminal assistant with persistent memory using Ollama and LanceDB.

## Features
- **Intelligent Memory**: Uses LanceDB to store and retrieve past interactions.
- **Code Execution**: Can suggest and run terminal commands (with user confirmation).
- **Non-Interactive Mode**: Run single requests directly from the CLI.
- **Sudo Support**: Handles sudo commands by running in a shell.

## Setup
1. **Ollama**: Ensure Ollama is running (`ollama serve`).
2. **Model**: Pull the default model:
   ```bash
   ollama pull dolphin-mistral:7b
   ```
3. **Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage
### Interactive Mode
```bash
python agent.py
```

### CLI Mode
```bash
python agent.py run "what is the current directory?"
```

## Internal Structure
- `agent.py`: Main entry point and orchestration.
- `ollama_client.py`: Wrapper for Ollama API.
- `memory_manager.py`: LanceDB interface for vector storage.
