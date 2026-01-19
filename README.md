# Terminal AI Agent

A powerful terminal assistant with persistent memory using Ollama and LanceDB.

## Features
- **Intelligent Memory**: Uses LanceDB to store and retrieve past interactions.
- **Code Execution**: Can suggest and run terminal commands (with user confirmation).
- **Non-Interactive Mode**: Run single requests directly from the CLI.
- **Sudo Support**: Handles sudo commands by running in a shell.

## Setup
1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd Agent
   ```
2. **Run the setup script**:
   This script installs dependencies, pulls the required model, and sets up a command alias.
   ```bash
   ./setup.sh
   source ~/.zshrc  # Or restart your terminal
   ```

## Usage
### CLI Mode (Recommended)
You can now use the `agent` command from anywhere:
```bash
agent "what is the current directory?"
```

### Interactive Mode
Start a chat session:
```bash
agent
```

## Internal Structure
- `agent.py`: Main entry point and orchestration.
- `ollama_client.py`: Wrapper for Ollama API.
- `memory_manager.py`: LanceDB interface for vector storage.
