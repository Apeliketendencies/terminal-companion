#!/usr/bin/env python3
import sys
import os
import argparse
import subprocess
import re
from ollama_client import OllamaClient
from memory_manager import MemoryManager

def run_command(command):
    print(f"\n--- Suggested Command ---\n{command}\n-------------------------")
    confirm = input("Execute this command? (y/n): ").strip().lower()
    if confirm == 'y':
        try:
            # Use shell=True to allow piping and sudo interactive prompts
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            if stdout:
                print(f"Output:\n{stdout}")
            if stderr:
                print(f"Error:\n{stderr}")
            return f"Command Output:\n{stdout}\n{stderr}"
        except Exception as e:
            print(f"Execution failed: {e}")
            return f"Execution failed: {e}"
    return "Command execution skipped by user."

def main():
    parser = argparse.ArgumentParser(description="Terminal AI Agent")
    parser.add_argument("command", nargs="*", help="CLI request to the agent")
    parser.add_argument("--run", action="store_true", help="Run the agent in CLI mode")
    args = parser.parse_args()

    # Configuration
    DB_PATH = "~/.lancedb"
    MODEL = "dolphin-mistral:7b"
    
    ollama = OllamaClient(model=MODEL)
    memory = MemoryManager(db_path=DB_PATH)

    system_prompt_base = (
        "You are a powerful terminal AI agent with intelligent memory. "
        "You can execute commands in the user's terminal by providing code blocks like this:\n"
        "```bash\n# your command here\n```\n"
        "Always explain what the command does before providing it. "
        "If sudo is needed, include it in the command. "
        "Use the provided context from memory if relevant.\n\n"
    )

    def process_request(request):
        # 1. Get embedding for query
        query_embedding = ollama.get_embeddings(request)

        # 2. Retrieve relevant context
        context_hits = memory.retrieve_context(query_embedding, top_k=3)
        context_str = "\n".join([f"- {content}" for content, dist in context_hits if dist < 1.0]) # LanceDB distance threshold

        # 3. Construct system prompt
        system_prompt = system_prompt_base + f"Context from Memory:\n{context_str or 'No relevant memory found.'}"

        # 4. Generate response
        print("AI: ", end="", flush=True)
        response_data = ollama.chat([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request}
        ])
        
        full_response = response_data['message']['content']
        print(full_response)

        # 5. Check for code blocks
        cmds = re.findall(r'```(?:bash|sh)\n(.*?)```', full_response, re.DOTALL)
        if cmds:
            for cmd in cmds:
                cmd_output = run_command(cmd.strip())
                # Optionally feed back the output to the agent
                # memory.store_interaction("system", cmd_output, ollama.get_embeddings(cmd_output))

        # 6. Store interaction
        response_embedding = ollama.get_embeddings(full_response)
        memory.store_interaction("user", request, query_embedding)
        memory.store_interaction("assistant", full_response, response_embedding)

    # CLI Mode: "run [request]" or just [request]
    if args.run and args.command:
        request = " ".join(args.command)
        process_request(request)
        return
    elif args.command:
        # Check if first arg is 'run'
        if args.command[0] == 'run':
            request = " ".join(args.command[1:])
            process_request(request)
            return

    # Interactive Mode
    print(f"--- Terminal AI Agent Activated (Model: {MODEL}) ---")
    print("Type 'exit' or 'quit' to end session.\n")

    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ['exit', 'quit']:
                break
            process_request(user_input)
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\nError: {e}")

if __name__ == "__main__":
    main()
