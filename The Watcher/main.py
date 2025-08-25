import threading
import json
import os
import subprocess
import time
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

fileDir = os.path.dirname(os.path.abspath(__file__))
configPath = os.path.join(fileDir, "config.json")

with open(configPath, "r") as f:
    config = json.load(f)

vaultPath = config.get("vaultPath")
debounce = config.get("debounceSeconds")
debounceTime = None

def gitSync():
    try:
        os.chdir(vaultPath)

        print("Checking for remote changes before commiting...")
        pullResult = subprocess.run(["git", "pull", "origin", config.get("repositoryBranch")], capture_output = True, text = True)

        status = subprocess.run(["git", "status", "--porcelain"], capture_output = True, text = True)
        if status.stdout.strip() == "":
            print("No changes to sync.")
            return
    
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = f"[Watcher] Auto-sync notes @ {timestamp}"
    
        subprocess.run(["git", "add", "."])
        commitResult = subprocess.run(["git", "commit", "-m", msg], capture_output = True, text = True)

        if commitResult.returncode == 0:
            print(f"Changes commited: {msg}")
            pushResult = subprocess.run(["git", "push", "origin", config.get("repositoryBranch")], capture_output = True, text = True)

            if pushResult.returncode == 0:
                print("Changes pushed to repository successfully.")
            else:
                print(f"Push failed: {pushResult.stderr}")
    
        else:
            print(f"Commit failed: {commitResult.stderr}")
    
    except Exception as e:
        print(f"Error during git sync: {e}")

def scheduleSync():
    global debounceTime
    if debounceTime:
        debounceTime.cancel()
    
    debounceTime = threading.Timer(debounce, gitSync)
    debounceTime.start()

class VaultHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if not event.is_directory:
            scheduleSync()

if __name__ == "__main__":
    try:
        eventHandler = VaultHandler()
        observer = Observer()
        observer.schedule(eventHandler, vaultPath, recursive = True)
        observer.start()

        print("Watcher is running...")
        print(f"Monitoring: {vaultPath}")

        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("Stopping the Watcher, final sync...")
        gitSync()
        observer.stop()
    observer.join()