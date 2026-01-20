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
    parser.add_argument("-e", "--endpoint", default="http://localhost:11434", help="Ollama API endpoint")
    parser.add_argument("-m", "--model", default="mistral-nemo:12b", help="LLM model to use")
    parser.add_argument("--embed-model", default="nomic-embed-text:latest", help="Model to use for embeddings")
    parser.add_argument("-y", "--yes", action="store_true", help="Auto-confirm all commands")
    args = parser.parse_args()

    # Specialized Units Configuration
    UNITS = {
        "GENERAL": args.model,
        "ARCHITECT": "qwen2.5-coder:1.5b",
        "SCRIBE": "smollm2:360m",
        "SCOUT": "gemma3:1b"
    }

    # Configuration
    DB_PATH = os.path.expanduser("~/.lancedb")
    EMBED_MODEL = args.embed_model
    
    ollama = OllamaClient(base_url=args.endpoint, model=args.model, embed_model=EMBED_MODEL)
    memory = MemoryManager(db_path=DB_PATH, model_name=EMBED_MODEL)

    PROMPTS = {
        "ARCHITECT": (
            "You are the ARCHITECT unit. Your job is to generate the exact bash command "
            "based on the GENERAL's request. Output ONLY the code block.\n"
            "Example: ```bash\nls -la\n```"
        ),
        "SCRIBE": (
            "You are the SCRIBE unit. Summarize the following terminal output into a concise summary. "
            "Highlight errors or key results. Keep it under 3 sentences."
        ),
        "SCOUT": (
            "You are the SCOUT unit. Analyze the following command for safety. "
            "If it is destructive (rm -rf, etc.) or highly risky, output 'RISK: [reason]'. "
            "Otherwise, output 'SAFE'."
        )
    }

    system_prompt_base = (
        f"You are the GENERAL (Mistral Nemo). You lead a team of specialized AI units:\n"
        f"- ARCHITECT ({UNITS['ARCHITECT']}): Generates precise bash commands.\n"
        f"- SCRIBE ({UNITS['SCRIBE']}): Summarizes large terminal outputs.\n"
        f"- SCOUT ({UNITS['SCOUT']}): Checks command safety.\n\n"
        "To execute a command, simply describe what you want to do in a code block with 'PLAN'. "
        "The ARCHITECT will then generate the bash for you.\n"
        "Example:\n"
        "```PLAN\nList all files in the current directory\n```\n"
        "Use the provided context from memory if relevant.\n\n"
    )

    MAX_TURNS = 5

    def process_request(request, auto_confirm=False):
        # 1. Get embedding for query
        query_embedding = ollama.get_embeddings(request)
        
        # Sync model name in case of auto-fallback
        memory.model_name = memory._sanitize_model_name(ollama.embed_model)

        # 2. Retrieve relevant context
        context_hits = memory.retrieve_context(query_embedding, top_k=3)
        context_str = "\n".join([f"- {content}" for content, dist in context_hits if dist < 0.7])

        # 3. Get system context
        system_env = get_system_context()

        # 4. Construct initial messages
        messages = [
            {"role": "system", "content": system_prompt_base + f"Context from Memory:\n{context_str or 'No relevant memory found.'}\n\n{system_env}"},
            {"role": "user", "content": request}
        ]

        current_auto_confirm = auto_confirm

        for turn in range(MAX_TURNS):
            # 5. Generate response (GENERAL)
            print(f"GENERAL ({UNITS['GENERAL']}) (Turn {turn+1}): ", end="", flush=True)
            
            prompt = ""
            system_msg = ""
            for msg in messages:
                if msg["role"] == "system":
                    system_msg = msg["content"]
                elif msg["role"] == "user":
                    prompt += f"\nUser: {msg['content']}\n"
                elif msg["role"] == "assistant":
                    prompt += f"\nAssistant: {msg['content']}\n"
            prompt += "\nAssistant: "

            try:
                # Use GENERAL model
                response_data = ollama.generate(prompt, system_prompt=system_msg, model=UNITS['GENERAL'])
            except Exception as e:
                print(f"Error communicating with AI: {e}")
                break
            
            full_response = response_data['response']
            print(full_response)
            messages.append({"role": "assistant", "content": full_response})

            # 6. Check for PLAN blocks (Delegation to ARCHITECT)
            plans = re.findall(r'```PLAN\n(.*?)```', full_response, re.DOTALL)
            
            # Also check for direct bash blocks just in case Nemo does it anyway
            direct_cmds = re.findall(r'```(?:bash|sh)\n(.*?)```', full_response, re.DOTALL)
            
            cmds_to_run = []

            # Delegate to ARCHITECT if plans exist
            for plan in plans:
                print(f"→ Delegating to ARCHITECT ({UNITS['ARCHITECT']})...")
                arch_resp = ollama.generate(f"GENERAL's PLAN: {plan.strip()}", system_prompt=PROMPTS['ARCHITECT'], model=UNITS['ARCHITECT'], keep_alive=0)
                arch_cmd_block = arch_resp['response']
                arch_cmds = re.findall(r'```(?:bash|sh)\n(.*?)```', arch_cmd_block, re.DOTALL)
                if arch_cmds:
                    cmds_to_run.extend(arch_cmds)
                else:
                    # Fallback: if Architect didn't wrap in bash, take the whole thing
                    cmds_to_run.append(arch_cmd_block.strip())

            # Add direct commands if any
            cmds_to_run.extend(direct_cmds)

            if not cmds_to_run:
                break

            # 7. Scout Check
            for cmd in list(cmds_to_run):
                scout_resp = ollama.generate(f"COMMAND: {cmd.strip()}", system_prompt=PROMPTS['SCOUT'], model=UNITS['SCOUT'], keep_alive=0)
                scout_eval = scout_resp['response'].strip()
                if "RISK" in scout_eval.upper():
                    print(f"→ SCOUT WARNING: {scout_eval}")
                    if not auto_confirm:
                        choice = input("Proceed anyway? (y/n): ").strip().lower()
                        if choice != 'y':
                            cmds_to_run.remove(cmd)
                            continue

            # Execute commands
            turn_outputs = []
            user_skipped = False

            for cmd in cmds_to_run:
                cmd_output, auto_confirm_now = run_command(cmd.strip(), auto_confirm=current_auto_confirm)
                if auto_confirm_now:
                    current_auto_confirm = True
                
                if "Command execution skipped by user" in cmd_output:
                    user_skipped = True
                    break
                
                # 8. Scribe Summarization for large outputs
                if len(cmd_output.splitlines()) > 15:
                    print(f"→ Large output. SCRIBE ({UNITS['SCRIBE']}) is summarizing...")
                    scribe_resp = ollama.generate(f"OUTPUT TO SUMMARIZE:\n{cmd_output}", system_prompt=PROMPTS['SCRIBE'], model=UNITS['SCRIBE'], keep_alive=0)
                    summary = scribe_resp['response']
                    cmd_output = f"SUMMARY OF LARGE OUTPUT:\n{summary}\n(Raw output was {len(cmd_output)} chars)"
                
                turn_outputs.append(cmd_output)
                memory.store_interaction("system", cmd_output, ollama.get_embeddings(cmd_output))

            if user_skipped:
                break

            if turn_outputs:
                combined_output = "\n".join(turn_outputs)
                messages.append({"role": "user", "content": f"Command output:\n{combined_output}\n\nPlease analyze and continue."})
            else:
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
    print(f"--- Terminal AI Agent Activated (Model: {args.model}) ---")
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
