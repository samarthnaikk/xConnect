# p2p_client.py
import requests
import sys
import json

def main():
    if len(sys.argv) < 2:
        print("Usage: python p2p_client.py <server_url>")
        print("Example: python p2p_client.py http://192.168.1.10:5001")
        return

    server_url = sys.argv[1]
    if not server_url.endswith('/echo'):
        server_url += '/echo'

    print(f"Connected to P2P entry node: {server_url}")
    print("Enter 'exit' or 'quit' to close the client.")
    print("Command format: [peer_alias@]command")
    print("Example 1 (local): ls -l")
    print("Example 2 (remote): machineB@pwd\n")

    while True:
        try:
            prompt = input(">> ")
            if prompt.lower() in ['exit', 'quit']:
                break
            if not prompt:
                continue

            payload = {'prompt': prompt}
            
            response = requests.post(server_url, json=payload)
            response_data = response.json()
            
            print("-" * 20)
            if response.status_code == 200:
                print(f"Command: {response_data.get('command', 'N/A')}")
                if 'output' in response_data:
                    # Don't print an empty "Output:" line if there's no output
                    if response_data['output']:
                        print("Output:")
                        print(response_data['output'])
                if 'message' in response_data:
                    print(f"Message: {response_data['message']}")
            else:
                print(f"Error (HTTP {response.status_code}):")
                # Pretty print the JSON error for readability
                print(json.dumps(response_data, indent=2))

            print("-" * 20)

        except requests.exceptions.RequestException as e:
            print(f"\n[Error] Could not connect to the server: {e}")
        except KeyboardInterrupt:
            print("\nExiting.")
            break
        except Exception as e:
            print(f"\n[An unexpected error occurred]: {e}")

if __name__ == '__main__':
    main()