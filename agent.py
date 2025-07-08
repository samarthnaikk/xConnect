# ==============================================================================
#  xConnect Unified Stateful Agent (agent.py)
#  - Correctly handles aliases AND environment changes (like 'export')
#    with a single, robust mechanism.
# ==============================================================================

import subprocess
import os
import requests
import time
import threading
import sys
from flask import Flask, request, jsonify

# --- AGENT CONFIGURATION ---
BROKER_URL = "https://x-connect-1sys9ova6-samarth-naiks-projects.vercel.app"
AGENT_ID = "my-desktop-agent"
MY_PUBLIC_ADDRESS = "https://3e9adf20dbd9.ngrok-free.app" # <-- Make sure this is your current ngrok URL
# --- END OF CONFIGURATION ---

# --- DO NOT EDIT BELOW THIS LINE ---
HEARTBEAT_INTERVAL = 30
LOCAL_PROFILE_FILENAME = "agentrc.zsh"
app = Flask(__name__)

# --- STATE MANAGEMENT: This dictionary stores the environment between commands ---
# It starts with the agent's base environment and is updated after every command.
AGENT_ENVIRONMENT = os.environ.copy()

def get_profile_path():
    project_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(project_dir, LOCAL_PROFILE_FILENAME)

def register_with_broker():
    # This function remains the same
    registration_url = f"{BROKER_URL}/register"
    payload = {"agent_id": AGENT_ID, "agent_address": MY_PUBLIC_ADDRESS}
    while True:
        try:
            print(f"Sending heartbeat to {registration_url}...")
            requests.post(registration_url, json=payload, timeout=10)
        except requests.exceptions.RequestException as e:
            print(f"Error: Could not send heartbeat to broker: {e}")
        time.sleep(HEARTBEAT_INTERVAL)

def parse_env_dump(env_dump):
    """Parses the output of the 'env' command into a dictionary."""
    new_env = {}
    for line in env_dump.strip().split('\n'):
        if '=' in line:
            key, value = line.split('=', 1)
            new_env[key] = value
    return new_env

@app.route('/execute', methods=['POST'])
def execute_command_on_agent():
    global AGENT_ENVIRONMENT # Declare that we will be modifying the global variable
    
    data = request.get_json()
    prompt = data.get('prompt').strip()
    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400

    print(f"Agent received prompt: '{prompt}'")

    local_profile_path = get_profile_path()
    if not os.path.exists(local_profile_path):
        return jsonify({"error": f"Agent profile '{LOCAL_PROFILE_FILENAME}' not found."}), 500

    # A unique separator to distinguish command output from the environment dump.
    env_separator = "__XCONNECT_ENV_SEPARATOR__"
    
    # This command does three things in sequence:
    # 1. Sources the profile to load aliases (like G).
    # 2. Runs the user's actual command (which might be an alias).
    # 3. Prints the separator, then dumps the *entire resulting environment*.
    # The semicolon ';' ensures step 3 runs even if the user's command fails.
    command_to_run = f"source {local_profile_path}; {prompt}; echo {env_separator}; env"
    
    try:
        result = subprocess.run(
            command_to_run,
            shell=True,
            capture_output=True,
            text=True,
            cwd=os.getcwd(),
            executable='/bin/zsh',
            env=AGENT_ENVIRONMENT  # Start with the environment from the *last* command
        )
        
        # Split the output into the command's actual output and the environment dump
        if env_separator in result.stdout:
            actual_output, env_dump = result.stdout.split(env_separator, 1)
            # Update our persistent environment with the new state from the shell
            AGENT_ENVIRONMENT = parse_env_dump(env_dump)
        else:
            # The command might have failed before it could print the environment
            actual_output = result.stdout

        response = {
            "output": actual_output.strip(),
            "error": result.stderr.strip(),
            "return_code": result.returncode
        }
        return jsonify(response), 200
            
    except Exception as e:
        return jsonify({"error": f"Agent execution failed: {str(e)}"}), 500

if __name__ == '__main__':
    # The main startup block remains the same
    print("✅ Unified Stateful Agent is starting...")
    heartbeat_thread = threading.Thread(target=register_with_broker, daemon=True)
    heartbeat_thread.start()
    app.run(host='0.0.0.0', port=5001)