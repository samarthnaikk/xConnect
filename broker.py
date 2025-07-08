# Save this file as broker.py for your Vercel/cloud server
# Don't forget to add 'requests' to your requirements.txt for Vercel

from flask import Flask, request, jsonify
import requests
import time
import threading

app = Flask(__name__)

# A thread-safe dictionary to store agent information
# Format: {"agent_id": {"address": "http://...", "last_seen": 167...}}
registered_agents = {}
agents_lock = threading.Lock()
AGENT_TIMEOUT = 90  # Seconds. If no heartbeat for this long, agent is considered dead.

@app.route('/register', methods=['POST'])
def register_agent():
    """Receives heartbeats and registration from agents."""
    data = request.get_json()
    agent_id = data.get('agent_id')
    agent_address = data.get('agent_address')

    if not agent_id or not agent_address:
        return jsonify({"error": "Registration requires 'agent_id' and 'agent_address'"}), 400

    with agents_lock:
        print(f"Received heartbeat from agent: '{agent_id}' at {agent_address}")
        registered_agents[agent_id] = {
            "address": agent_address,
            "last_seen": time.time()
        }
    return jsonify({"status": "ok", "message": f"Agent '{agent_id}' registered/updated."}), 200

@app.route('/forward', methods=['POST'])
def forward_command():
    data = request.get_json()
    agent_id = data.get('agent_id')
    prompt = data.get('prompt')

    if not agent_id or not prompt:
        return jsonify({"error": "Request must include 'agent_id' and 'prompt'"}), 400
    
    with agents_lock:
        agent = registered_agents.get(agent_id)

    if not agent:
        return jsonify({"error": f"Agent '{agent_id}' not found or is offline."}), 404

    # Check if agent is stale
    if time.time() - agent['last_seen'] > AGENT_TIMEOUT:
        return jsonify({"error": f"Agent '{agent_id}' is stale. Last seen {int(time.time() - agent['last_seen'])}s ago."}), 404

    agent_url = f"{agent['address']}/execute"
    print(f"Broker forwarding prompt '{prompt}' to agent '{agent_id}' at {agent_url}")

    try:
        response_from_agent = requests.post(agent_url, json={"prompt": prompt}, timeout=15)
        return response_from_agent.json(), response_from_agent.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Could not connect to agent '{agent_id}'", "details": str(e)}), 503

@app.route('/list_agents', methods=['GET'])
def list_agents():
    """An endpoint to see which agents are currently registered."""
    with agents_lock:
        # Create a copy to avoid issues while iterating
        current_agents = dict(registered_agents)
    
    # Prune stale agents from the view
    active_agents = {}
    for agent_id, info in current_agents.items():
        if time.time() - info['last_seen'] <= AGENT_TIMEOUT:
            active_agents[agent_id] = {
                "address": info['address'],
                "last_seen_ago_s": int(time.time() - info['last_seen'])
            }
            
    return jsonify(active_agents)

# For Vercel, you don't typically run with `app.run`. 
# Vercel's platform will run the 'app' object using a WSGI server like Gunicorn.
# The `if __name__ == '__main__':` block is for local testing.
if __name__ == '__main__':
    print("Broker Server for local testing on http://127.0.0.1:8000")
    app.run(port=8000, debug=True)