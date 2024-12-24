import requests
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading

# Central server URL
SERVER_URL = "http://<server-ip>:5002"

# Log and policy intervals
LOG_SEND_INTERVAL = 30  # 30 seconds
POLICY_FETCH_INTERVAL = 60  # 60 seconds

# Log list and current policy
logs = []
current_policy = []
observer = None  # Observer is defined globally

class DirectoryMonitorHandler(FileSystemEventHandler):
    """Handles file system events and logs them."""
    def __init__(self, agent_id):
        self.agent_id = agent_id

    def on_modified(self, event):
        if not event.is_directory:
            log_message = f"File modified: {event.src_path}"
            print(log_message)
            logs.append(log_message)

    def on_created(self, event):
        if not event.is_directory:
            log_message = f"File created: {event.src_path}"
            print(log_message)
            logs.append(log_message)

    def on_deleted(self, event):
        if not event.is_directory:
            log_message = f"File deleted: {event.src_path}"
            print(log_message)
            logs.append(log_message)

def register_agent(agent_id):
    """Registers the agent with the central server."""
    try:
        response = requests.post(f"{SERVER_URL}/register", json={"agent_id": agent_id})
        if response.status_code == 200:
            print(f"Agent {agent_id} registered successfully.")
        else:
            print(f"Failed to register agent {agent_id}.")
    except Exception as e:
        print(f"Error during registration: {e}")

def fetch_policy(agent_id):
    """Fetches policies from the central server and starts monitoring."""
    global current_policy, observer
    try:
        response = requests.get(f"{SERVER_URL}/get_policy/{agent_id}")
        if response.status_code == 200:
            policies = response.json().get("policies", [])
            if policies != current_policy:
                current_policy = policies
                print(f"Policies updated for agent {agent_id}: {policies}")
                # Start monitoring when new policies are fetched
                if observer:
                    observer.stop()
                    observer.join()
                if current_policy:
                    directory = current_policy[0].get("directory", None)
                    if directory:
                        event_handler = DirectoryMonitorHandler(agent_id)
                        observer = Observer()
                        observer.schedule(event_handler, path=directory, recursive=True)
                        observer.start()
                        print(f"Monitoring started for directory: {directory}")
        else:
            print(f"No policies found for agent {agent_id}.")
    except Exception as e:
        print(f"Error fetching policies: {e}")

def send_logs(agent_id):
    """Sends collected logs to the central server."""
    global logs
    while True:
        if logs:
            try:
                print("Sending logs to server...")
                response = requests.post(f"{SERVER_URL}/logs", json={"agent_id": agent_id, "logs": logs})
                if response.status_code == 200:
                    print("Logs sent successfully.")
                    logs = []  # Clear logs after successful transmission
                else:
                    print(f"Failed to send logs. Status code: {response.status_code}")
            except Exception as e:
                print(f"Error sending logs: {e}")
        time.sleep(LOG_SEND_INTERVAL)

def monitor_directory(agent_id):
    """Periodically checks for updated policies."""
    while True:
        fetch_policy(agent_id)
        time.sleep(POLICY_FETCH_INTERVAL)

if __name__ == '__main__':
    AGENT_ID = "agent-1"

    # Register the agent with the central server
    register_agent(AGENT_ID)

    # Start the log sending process in a separate thread
    log_thread = threading.Thread(target=send_logs, args=(AGENT_ID,), daemon=True)
    log_thread.start()

    # Start monitoring directories based on policies
    monitor_thread = threading.Thread(target=monitor_directory, args=(AGENT_ID,), daemon=True)
    monitor_thread.start()

    # Keep the main program running indefinitely
    while True:
        time.sleep(1)
