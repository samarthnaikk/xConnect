# p2p_server.py
from flask import Flask, request, jsonify
import subprocess
import os
import requests
import sys

# --- P2P Configuration ---
# IMPORTANT: You must configure this section on each machine.

# Give this machine a unique alias.
# On machine A, set this to 'machineA'. On machine B, set to 'machineB'.
# In p2p_server.py on Machine A
MY_ALIAS = 'machineB' 
PEERS = {
    'machineA': 'http://192.168.9.9:5001',
    'machineB': 'http://192.168.9.155:5001',
}
# -------------------------

app = Flask(__name__)

def execute_local_command(prompt):
    """
    This function contains the original logic to execute a command on the local machine.
    """
    print(f"Executing local command: {prompt}")

    direct_commands = ["cd ", "ls", "mkdir ", "pwd", "echo ", "rm ", "cat ", "touch "]
    is_direct_command = any(prompt.startswith(cmd) for cmd in direct_commands)

    if not is_direct_command:
        print(f"Indirect prompt received: {prompt}")
        return jsonify({"type": "indirect_prompt", "message": f"Indirect prompt received: {prompt}"}), 200

    try:
        if prompt.startswith("cd "):
            target_dir = prompt[3:].strip()
            # Basic security check to prevent traversing up too far
            if '..' in target_dir:
                 return jsonify({"type": "direct_command_output", "command": prompt, "error": "Relative paths with '..' are not allowed for security reasons."}), 400
            
            # Change to absolute path to be safe
            if not os.path.isabs(target_dir):
                target_dir = os.path.join(os.getcwd(), target_dir)

            if os.path.isdir(target_dir):
                os.chdir(target_dir)
                output = f"Changed directory to: {os.getcwd()}"
                return jsonify({"type": "direct_command_output", "command": prompt, "output": output}), 200
            else:
                return jsonify({"type": "direct_command_output", "command": prompt, "error": f"Directory not found: {target_dir}"}), 404
        else:
            # Using os.getcwd() to ensure commands run in the current working directory
            result = subprocess.run(prompt, shell=True, capture_output=True, text=True, cwd=os.getcwd())
            output = result.stdout.strip()
            error = result.stderr.strip()

            if result.returncode == 0:
                return jsonify({"type": "direct_command_output", "command": prompt, "output": output}), 200
            else:
                return jsonify({"type": "direct_command_output", "command": prompt, "error": error, "output": output}), 500
    except Exception as e:
        return jsonify({"type": "direct_command_output", "command": prompt, "error": str(e)}), 500

@app.route('/echo', methods=['POST'])
def echo_prompt():
    data = request.get_json()
    if not data or 'prompt' not in data:
        return jsonify({"error": "No prompt provided in JSON payload"}), 400

    prompt = data['prompt']
    print(f"Received request with prompt: {prompt}")

    # Check if the command is targeted for a peer
    if '@' in prompt:
        target_alias, command_to_run = prompt.split('@', 1)
        
        if target_alias == MY_ALIAS:
            # Command is explicitly for this machine
            return execute_local_command(command_to_run)
        
        elif target_alias in PEERS:
            # Forward the command to the correct peer
            peer_url = PEERS[target_alias]
            print(f"Forwarding command '{command_to_run}' to peer '{target_alias}' at {peer_url}")
            try:
                # The payload for the peer does not include the alias
                payload = {'prompt': command_to_run}
                response = requests.post(f"{peer_url}/echo", json=payload, timeout=10) # 10-second timeout
                # Return the peer's response directly to the original client
                return jsonify(response.json()), response.status_code
            except requests.exceptions.RequestException as e:
                error_message = f"Failed to connect to peer '{target_alias}': {e}"
                print(error_message)
                return jsonify({"type": "p2p_error", "error": error_message}), 504 # Gateway Timeout
        else:
            return jsonify({"type": "p2p_error", "error": f"Unknown peer alias: '{target_alias}'"}), 404

    else:
        # No alias provided, execute locally
        return execute_local_command(prompt)

if __name__ == '__main__':
    if '<' in PEERS['machineA'] or '<' in PEERS['machineB']:
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!!! ERROR: Please configure your peer IP addresses   !!!")
        print("!!! in the PEERS dictionary in p2p_server.py.      !!!")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        sys.exit(1)

    print(f"Starting server for peer '{MY_ALIAS}'...")
    print(f"My CWD is: {os.getcwd()}")
    # IMPORTANT: host='0.0.0.0' makes the server accessible on your network
    app.run(host='0.0.0.0', port=5001)