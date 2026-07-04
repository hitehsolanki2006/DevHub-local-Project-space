import os
import socket
import subprocess
import threading
import sys
import json

# Thread-safe dictionary to keep track of active project servers
# Structure: { project_path: { "process": Popen, "port": int, "thread": Thread, "logs": list } }
ACTIVE_RUNS = {}
ACTIVE_RUNS_LOCK = threading.Lock()
LOG_HISTORY = {}

def is_port_in_use(port):
    """Check if a port is currently in use on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return False
        except socket.error:
            return True

def find_free_port(start_port=3000, max_attempts=100):
    """Find the first available port starting from start_port."""
    port = start_port
    for _ in range(max_attempts):
        if not is_port_in_use(port):
            return port
        port += 1
    return None

def get_node_scripts(project_path):
    """Parse package.json and return dictionary of scripts."""
    pkg_path = os.path.join(project_path, "package.json")
    if not os.path.exists(pkg_path):
        return {}
    try:
        with open(pkg_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("scripts", {})
    except Exception:
        return {}

def log_reader_thread(proc, project_path, log_callback):
    """Target function for background thread reading process stdout/stderr."""
    # Read output line by line
    while True:
        line = proc.stdout.readline()
        if not line:
            break
        
        # Decode and format line
        try:
            decoded_line = line.decode("utf-8", errors="replace")
        except Exception:
            decoded_line = str(line)
            
        with ACTIVE_RUNS_LOCK:
            if project_path in ACTIVE_RUNS:
                ACTIVE_RUNS[project_path]["logs"].append(decoded_line)
            
            # Store in persistent log history
            if project_path not in LOG_HISTORY:
                LOG_HISTORY[project_path] = []
            LOG_HISTORY[project_path].append(decoded_line)
                
        if log_callback:
            log_callback(project_path, decoded_line)
            
    # Process ended
    proc.wait()
    with ACTIVE_RUNS_LOCK:
        if project_path in ACTIVE_RUNS:
            # Only remove if it's the same process
            if ACTIVE_RUNS[project_path]["process"] == proc:
                ACTIVE_RUNS.pop(project_path)
        
        # Append termination marker
        term_line = "[Server Process Terminated]\n"
        if project_path not in LOG_HISTORY:
            LOG_HISTORY[project_path] = []
        LOG_HISTORY[project_path].append(term_line)
        
    if log_callback:
        log_callback(project_path, term_line)

def run_project(project_path, project_type, command_override=None, target_port=None, log_callback=None):
    """Launch the project server.
    Args:
        project_path (str): Root path of project
        project_type (str): 'Node.js', 'Python', etc.
        command_override (str): Manual command to run instead of automatic guess
        target_port (int): Port to run on (if applicable)
        log_callback (callable): Function called with (project_path, log_line)
    Returns:
        tuple: (success (bool), message (str), port (int or None))
    """
    with ACTIVE_RUNS_LOCK:
        if project_path in ACTIVE_RUNS:
            return False, "Project is already running.", ACTIVE_RUNS[project_path]["port"]

    # Determine command to run
    cmd = []
    env = os.environ.copy()
    port = None

    if command_override:
        # User specified a manual command override
        cmd = command_override.split()
    elif project_type == "Node.js":
        # Guess Node.js startup
        scripts = get_node_scripts(project_path)
        # Select best script (prefer dev, then start, then first available script)
        script_to_run = "dev"
        if "dev" not in scripts:
            if "start" in scripts:
                script_to_run = "start"
            elif scripts:
                script_to_run = list(scripts.keys())[0]
            else:
                script_to_run = None

        if not script_to_run:
            return False, "No npm scripts found in package.json", None

        # Check port
        port = target_port if target_port else 3000
        if is_port_in_use(port):
            # Port busy; find a free one
            free_port = find_free_port(start_port=port)
            if not free_port:
                return False, f"Could not find an available port starting from {port}.", None
            port = free_port

        # Inject port into environment variables (standard for Node apps)
        env["PORT"] = str(port)
        
        # Use npm script command
        # On Windows, npm is a cmd/ps file, so we run through shell or direct cmd.exe invocation
        cmd = ["npm", "run", script_to_run]
    elif project_type == "Python":
        # Python runner - check for standard entry points
        entries = ["main.py", "app.py", "manage.py", "wsgi.py"]
        run_file = None
        for entry in entries:
            if os.path.exists(os.path.join(project_path, entry)):
                run_file = entry
                break
        
        if not run_file:
            return False, "No standard python entry points found (main.py, app.py, etc.)", None
            
        # Determine python executable (prefer venv python if exists)
        python_exe = sys.executable  # default to current python
        venv_paths = [
            os.path.join(project_path, "venv", "Scripts", "python.exe"),
            os.path.join(project_path, ".venv", "Scripts", "python.exe")
        ]
        for venv in venv_paths:
            if os.path.exists(venv):
                python_exe = venv
                break
                
        cmd = [python_exe, run_file]
    else:
        # Static HTML or unknown
        # We can run a simple Python HTTP server to serve static HTML projects!
        port = target_port if target_port else 8000
        if is_port_in_use(port):
            free_port = find_free_port(start_port=port)
            if not free_port:
                return False, "Could not find a free port.", None
            port = free_port

        cmd = [sys.executable, "-m", "http.server", str(port)]

    cmd_str = " ".join(cmd)
    with ACTIVE_RUNS_LOCK:
        LOG_HISTORY[project_path] = [f"[Starting Server]: {cmd_str}\n"]

    try:
        # Start subprocess
        # On Windows, we use shell=True for npm commands or CREATE_NO_WINDOW flags to hide cmd shells
        # taskkill needs the process pid, so we keep a reference
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        proc = subprocess.Popen(
            cmd,
            cwd=project_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
            startupinfo=startupinfo,
            shell=(sys.platform == "win32" and cmd[0] == "npm") # use shell for npm cmd script
        )
        
        # Spawn thread to read outputs
        t = threading.Thread(target=log_reader_thread, args=(proc, project_path, log_callback), daemon=True)
        t.start()

        with ACTIVE_RUNS_LOCK:
            ACTIVE_RUNS[project_path] = {
                "process": proc,
                "port": port,
                "thread": t,
                "logs": [],
                "command": cmd_str
            }

        return True, "Server started successfully.", port
    except Exception as e:
        err_msg = f"[Startup Error]: Failed to start server: {e}\n"
        with ACTIVE_RUNS_LOCK:
            if project_path not in LOG_HISTORY:
                LOG_HISTORY[project_path] = []
            LOG_HISTORY[project_path].append(err_msg)
        if log_callback:
            log_callback(project_path, err_msg)
        return False, f"Failed to start server: {e}", None

def stop_project(project_path):
    """Stop the running server for the given project path."""
    with ACTIVE_RUNS_LOCK:
        if project_path not in ACTIVE_RUNS:
            return False, "Project is not running."
        run_data = ACTIVE_RUNS[project_path]
        proc = run_data["process"]

    try:
        if sys.platform == "win32":
            # On Windows, terminating a Popen process doesn't kill child processes spawned by it (like npm spawning node).
            # We use taskkill to kill the whole process tree.
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        else:
            proc.terminate()
            proc.wait(timeout=2)
    except Exception as e:
        # Fallback to simple kill if taskkill fails
        try:
            proc.kill()
        except Exception:
            pass
        
    return True, "Project stopped."

def get_running_projects():
    """Get active runs info."""
    with ACTIVE_RUNS_LOCK:
        return {path: {"port": data["port"], "command": data["command"]} for path, data in ACTIVE_RUNS.items()}

def get_project_logs(project_path):
    """Get accumulated logs for a project."""
    with ACTIVE_RUNS_LOCK:
        if project_path in LOG_HISTORY:
            return "".join(LOG_HISTORY[project_path])
        return ""

def clear_project_logs(project_path):
    """Wipe accumulated logs for a project."""
    with ACTIVE_RUNS_LOCK:
        LOG_HISTORY[project_path] = []
