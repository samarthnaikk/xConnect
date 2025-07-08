from flask import Flask, request
import subprocess
import os

app = Flask(__name__)

@app.route('/echo', methods=['POST'])
def echo_prompt():
    data = request.get_json()
    prompt = data.get('prompt')

    if not prompt:
        return {"error": "No prompt provided"}, 400

    print(f"Received prompt: {prompt}") # Still print all prompts to the server terminal

    # List of direct commands that can be executed
    # Added common commands like pwd, echo, rm, cat, touch
    direct_commands = ["cd ", "ls", "mkdir ", "pwd", "echo ", "rm ", "cat ", "touch "]
    is_direct_command = False
    for cmd_prefix in direct_commands:
        if prompt.startswith(cmd_prefix):
            is_direct_command = True
            break

    if is_direct_command:
        try:
            # Handle 'cd' separately as it changes the process's CWD
            if prompt.startswith("cd "):
                target_dir = prompt[3:].strip()
                if os.path.isdir(target_dir):
                    os.chdir(target_dir)
                    output = f"Changed directory to: {os.getcwd()}"
                    return {"type": "direct_command_output", "command": prompt, "output": output}, 200
                else:
                    return {"type": "direct_command_output", "command": prompt, "error": f"Directory not found: {target_dir}"}, 400
            else:
                # For other direct commands (ls, mkdir, pwd, echo, rm, cat, touch)
                result = subprocess.run(prompt, shell=True, capture_output=True, text=True, cwd=os.getcwd())
                output = result.stdout.strip()
                error = result.stderr.strip()

                if result.returncode == 0:
                    return {"type": "direct_command_output", "command": prompt, "output": output}, 200
                else:
                    return {"type": "direct_command_output", "command": prompt, "error": error, "output": output}, 500
        except Exception as e:
            return {"type": "direct_command_output", "command": prompt, "error": str(e)}, 500
    else:
        print(f"Indirect prompt received: {prompt}")
        return {"type": "indirect_prompt", "message": f"Indirect prompt received: {prompt}"}, 200

if __name__ == '__main__':
    app.run(port=5001)