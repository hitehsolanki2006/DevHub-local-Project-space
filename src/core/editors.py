import os
import winreg
import subprocess

COMMON_EDITORS = {
    "VS Code": {
        "registry_paths": [
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\App Paths\code.exe"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\App Paths\code.exe")
        ],
        "default_paths": [
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
            r"C:\Program Files\Microsoft VS Code\Code.exe",
            r"C:\Program Files (x86)\Microsoft VS Code\Code.exe"
        ]
    },
    "Cursor": {
        "registry_paths": [
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\App Paths\cursor.exe"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\App Paths\cursor.exe")
        ],
        "default_paths": [
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\cursor\Cursor.exe")
        ]
    },
    "Notepad++": {
        "registry_paths": [
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\App Paths\notepad++.exe")
        ],
        "default_paths": [
            r"C:\Program Files\Notepad++\notepad++.exe",
            r"C:\Program Files (x86)\Notepad++\notepad++.exe"
        ]
    },
    "Sublime Text": {
        "registry_paths": [
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\App Paths\sublime_text.exe")
        ],
        "default_paths": [
            r"C:\Program Files\Sublime Text\sublime_text.exe",
            r"C:\Program Files\Sublime Text 3\sublime_text.exe"
        ]
    },
    "PyCharm": {
        "registry_paths": [
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\App Paths\pycharm64.exe"),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\App Paths\pycharm64.exe"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\App Paths\pycharm.exe")
        ],
        "default_paths": [
            os.path.expandvars(r"%PROGRAMFILES%\JetBrains\PyCharm\bin\pycharm64.exe")
        ]
    },
    "WebStorm": {
        "registry_paths": [
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\App Paths\webstorm64.exe"),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\App Paths\webstorm64.exe")
        ],
        "default_paths": [
            os.path.expandvars(r"%PROGRAMFILES%\JetBrains\WebStorm\bin\webstorm64.exe")
        ]
    },
    "IntelliJ IDEA": {
        "registry_paths": [
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\App Paths\idea64.exe"),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\App Paths\idea64.exe")
        ],
        "default_paths": [
            os.path.expandvars(r"%PROGRAMFILES%\JetBrains\IntelliJ IDEA\bin\idea64.exe")
        ]
    },
    "CLion": {
        "registry_paths": [
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\App Paths\clion64.exe"),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\App Paths\clion64.exe")
        ],
        "default_paths": [
            os.path.expandvars(r"%PROGRAMFILES%\JetBrains\CLion\bin\clion64.exe")
        ]
    },
    "Kiro": {
        "registry_paths": [
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\App Paths\kiro.exe"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\App Paths\kiro.exe")
        ],
        "default_paths": [
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\kiro\Kiro.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Kiro\Kiro.exe"),
            r"C:\Program Files\Kiro\Kiro.exe"
        ]
    },
    "Antigravity": {
        "registry_paths": [
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\App Paths\antigravity.exe"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\App Paths\antigravity.exe")
        ],
        "default_paths": [
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\antigravity\Antigravity.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Antigravity\Antigravity.exe"),
            os.path.expandvars(r"%APPDATA%\.gemini\antigravity\Antigravity.exe"),
            os.path.expandvars(r"%USERPROFILE%\.gemini\antigravity\Antigravity.exe")
        ]
    }
}

def check_registry_path(hive, subkey):
    """Check registry key for default string value (which contains the exe path)."""
    try:
        with winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ) as key:
            val = winreg.QueryValue(key, "")
            if val:
                val = val.strip('"')
                if os.path.exists(val):
                    return os.path.normpath(val)
    except OSError:
        pass
    return None

def detect_editors():
    """Detect available editors on the system.
    Returns:
        dict: {EditorName: ExecutablePath}
    """
    detected = {}
    
    # Check common editors list
    for name, config in COMMON_EDITORS.items():
        found = False
        # 1. Try registry
        for hive, subkey in config["registry_paths"]:
            path = check_registry_path(hive, subkey)
            if path:
                detected[name] = path
                found = True
                break
        
        # 2. Try default filesystem paths
        if not found:
            for path in config["default_paths"]:
                if os.path.exists(path):
                    detected[name] = os.path.normpath(path)
                    break
                    
    return detected

def open_in_editor(editor_name, editor_path, project_path):
    """Open project folder in selected editor.
    Args:
        editor_name (str): Name of the editor (e.g. 'VS Code')
        editor_path (str): Full path to executable
        project_path (str): Full path to project directory
    """
    if not editor_path or not os.path.exists(editor_path):
        return False, "Editor executable not found."
    
    try:
        # Command syntax can differ; standard is launching exe with folder as arg
        # VS Code and Cursor support: `<exe> <folder>`
        # Notepad++ support: `<exe> -openFolder <folder>` (or just opening files)
        cmd = [editor_path, project_path]
        
        if "notepad++" in editor_path.lower():
            # Notepad++ open folder command
            cmd = [editor_path, "-openFolder", project_path]
            
        # Run process detached so it does not block our GUI and redirect logs to DEVNULL
        subprocess.Popen(
            cmd, 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL, 
            creationflags=subprocess.DETACHED_PROCESS
        )
        return True, "Editor launched successfully."
    except Exception as e:
        return False, f"Failed to open project in editor: {e}"
