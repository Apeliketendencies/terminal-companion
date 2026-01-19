#!/usr/bin/env python3
import sys
import os
import argparse
import subprocess
import re
from ollama_client import OllamaClient
from memory_manager import MemoryManager

def run_command(command, auto_confirm=False):
    print(f"\n--- Suggested Command ---\n{command}\n-------------------------")
    if auto_confirm:
        confirm = 'y'
        print("Auto-executing...")
    else:
        confirm = input("Execute this command? (y/n/a - yes/no/always): ").strip().lower()

    if confirm in ['y', 'a']:
        try:
            # Use shell=True to allow piping and sudo interactive prompts
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            if stdout:
                print(f"Output:\n{stdout}")
            if stderr:
                print(f"Error:\n{stderr}")
            return f"Command Output:\n{stdout}\n{stderr}", (confirm == 'a')
        except Exception as e:
            print(f"Execution failed: {e}")
            return f"Execution failed: {e}", False
    return "Command execution skipped by user.", False

def get_system_context():
    try:
        cwd = os.getcwd()
        user = os.getenv("USER", "unknown")
        # Get a brief look at the files in the current dir
        files = subprocess.check_output("ls -F | head -n 20", shell=True, text=True).strip()
        context = (
            f"--- System Environment ---\n"
            f"User: {user}\n"
            f"Current Directory: {cwd}\n"
            f"Files in CWD (top 20):\n{files}\n"
            f"---------------------------\n"
        )
        return context
    except Exception as e:
        return f"Error gathering system context: {e}"

def main():
    parser = argparse.ArgumentParser(description="Terminal AI Agent")
    parser.add_argument("command", nargs="*", help="CLI request to the agent")
    parser.add_argument("--run", action="store_true", help="Run the agent in CLI mode")
    parser.add_argument("-y", "--yes", action="store_true", help="Auto-confirm all commands")
    args = parser.parse_args()

    # Configuration
    DB_PATH = "~/.lancedb"
    MODEL = "nemo-agent"
    
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

    MAX_TURNS = 5

    def process_request(request, auto_confirm=False):
        # 1. Get embedding for query
        query_embedding = ollama.get_embeddings(request)

        # 2. Retrieve relevant context
        context_hits = memory.retrieve_context(query_embedding, top_k=3)
        context_str = "\n".join([f"- {content}" for content, dist in context_hits if dist < 0.7]) # Cosine distance threshold

        # 3. Get system context
        system_env = get_system_context()

        # 4. Construct initial messages
        messages = [
            {"role": "system", "content": system_prompt_base + f"Context from Memory:\n{context_str or 'No relevant memory found.'}\n\n{system_env}"},
            {"role": "user", "content": request}
        ]

        current_auto_confirm = auto_confirm

        for turn in range(MAX_TURNS):
            # 5. Generate response
            print(f"AI (Turn {turn+1}): ", end="", flush=True)
            try:
                response_data = ollama.chat(messages)
            except Exception as e:
                print(f"Error communicating with AI: {e}")
                break
            
            full_response = response_data['message']['content']
            print(full_response)
            
            # Add assistant's response to message history
            messages.append({"role": "assistant", "content": full_response})

            # 6. Check for code blocks
            cmds = re.findall(r'```(?:bash|sh)\n(.*?)```', full_response, re.DOTALL)
            
            if not cmds:
                # No more commands, we are likely done
                break

            # Execute commands and collect output
            turn_outputs = []
            user_skipped = False

            for cmd in cmds:
                cmd_output, auto_confirm_now = run_command(cmd.strip(), auto_confirm=current_auto_confirm)
                if auto_confirm_now:
                    current_auto_confirm = True
                
                if "Command execution skipped by user" in cmd_output:
                    user_skipped = True
                    break
                
                turn_outputs.append(cmd_output)
                # Store system output in memory immediately for cross-session awareness
                memory.store_interaction("system", cmd_output, ollama.get_embeddings(cmd_output))

            if user_skipped:
                print("User skipped execution. Ending loop.")
                break

            if turn_outputs:
                # Feed the output back into the conversation for the next turn
                combined_output = "\n".join(turn_outputs)
                messages.append({"role": "user", "content": f"Command output:\n{combined_output}\n\nPlease analyze the output and continue if needed."})
            else:
                # This shouldn't really happen if cmds existed and weren't skipped
                break

        # 7. Store final interaction to memory
        response_embedding = ollama.get_embeddings(full_response)
        memory.store_interaction("user", request, query_embedding)
        memory.store_interaction("assistant", full_response, response_embedding)

    # CLI Mode: "run [request]" or just [request]
    if args.command:
        # If the first word is 'run', we treat the rest as the request
        if args.command[0] == 'run':
            request = " ".join(args.command[1:])
        else:
            request = " ".join(args.command)
        
        if request:
            process_request(request, auto_confirm=args.yes)
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
            process_request(user_input, auto_confirm=args.yes)
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\nError: {e}")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
import sys
import os
import argparse
import subprocess
import re
from ollama_client import OllamaClient
from memory_manager import MemoryManager

def run_command(command, auto_confirm=False):
    print(f"\n--- Suggested Command ---\n{command}\n-------------------------")
    if auto_confirm:
        confirm = 'y'
        print("Auto-executing...")
    else:
        confirm = input("Execute this command? (y/n/a - yes/no/always): ").strip().lower()

    if confirm in ['y', 'a']:
        try:
            # Use shell=True to allow piping and sudo interactive prompts
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            if stdout:
                print(f"Output:\n{stdout}")
            if stderr:
                print(f"Error:\n{stderr}")
            return f"Command Output:\n{stdout}\n{stderr}", (confirm == 'a')
        except Exception as e:
            print(f"Execution failed: {e}")
            return f"Execution failed: {e}", False
    return "Command execution skipped by user.", False

def get_system_context():
    try:
        cwd = os.getcwd()
        user = os.getenv("USER", "unknown")
        # Get a brief look at the files in the current dir
        files = subprocess.check_output("ls -F | head -n 20", shell=True, text=True).strip()
        context = (
            f"--- System Environment ---\n"
            f"User: {user}\n"
            f"Current Directory: {cwd}\n"
            f"Files in CWD (top 20):\n{files}\n"
            f"---------------------------\n"
        )
        return context
    except Exception as e:
        return f"Error gathering system context: {e}"

def main():
    parser = argparse.ArgumentParser(description="Terminal AI Agent")
    parser.add_argument("command", nargs="*", help="CLI request to the agent")
    parser.add_argument("--run", action="store_true", help="Run the agent in CLI mode")
    parser.add_argument("-y", "--yes", action="store_true", help="Auto-confirm all commands")
    args = parser.parse_args()

    # Configuration
    DB_PATH = "~/.lancedb"
    MODEL = "nemo-agent"
    
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

    MAX_TURNS = 5

    def process_request(request, auto_confirm=False):
        # 1. Get embedding for query
        query_embedding = ollama.get_embeddings(request)

        # 2. Retrieve relevant context
        context_hits = memory.retrieve_context(query_embedding, top_k=3)
        context_str = "\n".join([f"- {content}" for content, dist in context_hits if dist < 0.7]) # Cosine distance threshold

        # 3. Get system context
        system_env = get_system_context()

        # 4. Construct initial messages
        messages = [
            {"role": "system", "content": system_prompt_base + f"Context from Memory:\n{context_str or 'No relevant memory found.'}\n\n{system_env}"},
            {"role": "user", "content": request}
        ]

        current_auto_confirm = auto_confirm

        for turn in range(MAX_TURNS):
            # 5. Generate response
            print(f"AI (Turn {turn+1}): ", end="", flush=True)
            try:
                response_data = ollama.chat(messages)
            except Exception as e:
                print(f"Error communicating with AI: {e}")
                break
            
            full_response = response_data['message']['content']
            print(full_response)
            
            # Add assistant's response to message history
            messages.append({"role": "assistant", "content": full_response})

            # 6. Check for code blocks
            cmds = re.findall(r'```(?:bash|sh)\n(.*?)```', full_response, re.DOTALL)
            
            if not cmds:
                # No more commands, we are likely done
                break

            # Execute commands and collect output
            turn_outputs = []
            user_skipped = False

            for cmd in cmds:
                cmd_output, auto_confirm_now = run_command(cmd.strip(), auto_confirm=current_auto_confirm)
                if auto_confirm_now:
                    current_auto_confirm = True
                
                if "Command execution skipped by user" in cmd_output:
                    user_skipped = True
                    break
                
                turn_outputs.append(cmd_output)
                # Store system output in memory immediately for cross-session awareness
                memory.store_interaction("system", cmd_output, ollama.get_embeddings(cmd_output))

            if user_skipped:
                print("User skipped execution. Ending loop.")
                break

            if turn_outputs:
                # Feed the output back into the conversation for the next turn
                combined_output = "\n".join(turn_outputs)
                messages.append({"role": "user", "content": f"Command output:\n{combined_output}\n\nPlease analyze the output and continue if needed."})
            else:
                # This shouldn't really happen if cmds existed and weren't skipped
                break

        # 7. Store final interaction to memory
        response_embedding = ollama.get_embeddings(full_response)
        memory.store_interaction("user", request, query_embedding)
        memory.store_interaction("assistant", full_response, response_embedding)

    # CLI Mode: "run [request]" or just [request]
    if args.command:
        # If the first word is 'run', we treat the rest as the request
        if args.command[0] == 'run':
            request = " ".join(args.command[1:])
        else:
            request = " ".join(args.command)
        
        if request:
            process_request(request, auto_confirm=args.yes)
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
            process_request(user_input, auto_confirm=args.yes)
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\nError: {e}")

if __name__ == "__main__":
    main()
