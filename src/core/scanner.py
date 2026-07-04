import os
import ctypes
import sys

# Define target project file names and types
PROJECT_SIGNATURES = {
    "package.json": "Node.js",
    "requirements.txt": "Python",
    "pyproject.toml": "Python",
    "Pipfile": "Python",
    "Cargo.toml": "Rust",
    "go.mod": "Go",
    "CMakeLists.txt": "C/C++",
    "Makefile": "C/C++",
    "pom.xml": "Java/Kotlin",
    "build.gradle": "Java/Kotlin",
    "build.gradle.kts": "Java/Kotlin",
    "composer.json": "PHP",
    "Gemfile": "Ruby",
    "index.html": "HTML/CSS"
}

SKIP_DIRS = {
    ".git", "node_modules", "venv", ".venv", "__pycache__", 
    "dist", "build", "target", "bin", "obj", ".idea", ".vscode"
}

def python_scan(current_path, depth, max_depth, callback):
    """Fallback pure Python directory scanner mimicking the C implementation."""
    if depth > max_depth:
        return

    try:
        entries = list(os.scandir(current_path))
    except OSError:
        return

    is_project = False
    project_type = ""
    subdirs = []

    # First pass: check for project files in current directory
    for entry in entries:
        try:
            if entry.is_file():
                name = entry.name
                if name == "package.json":
                    is_project = True
                    project_type = "Node.js"
                    break
                elif name in ("requirements.txt", "pyproject.toml", "Pipfile"):
                    is_project = True
                    project_type = "Python"
                    break
                elif name == "Cargo.toml":
                    is_project = True
                    project_type = "Rust"
                    break
                elif name == "go.mod":
                    is_project = True
                    project_type = "Go"
                    break
                elif name in ("CMakeLists.txt", "Makefile"):
                    is_project = True
                    project_type = "C/C++"
                    break
                elif name in ("pom.xml", "build.gradle", "build.gradle.kts"):
                    is_project = True
                    project_type = "Java/Kotlin"
                    break
                elif name.endswith(".csproj") or name.endswith(".sln"):
                    is_project = True
                    project_type = "C#/.NET"
                    break
                elif name == "composer.json":
                    is_project = True
                    project_type = "PHP"
                    break
                elif name == "Gemfile":
                    is_project = True
                    project_type = "Ruby"
                    break
                elif name == "index.html" and not project_type:
                    is_project = True
                    project_type = "HTML/CSS"
            elif entry.is_dir():
                if entry.name not in SKIP_DIRS:
                    subdirs.append(entry.path)
        except OSError:
            continue

    if is_project:
        callback(os.path.normpath(current_path), project_type)
        return

    # Second pass: recurse into subdirectories
    for subdir in subdirs:
        python_scan(subdir, depth + 1, max_depth, callback)

def scan_directory(root_path, max_depth=2):
    """Scan a directory for projects using C DLL or Python fallback.
    Returns:
        list of dict: [{"name": str, "path": str, "type": str}]
    """
    found_projects = []

    def on_project_found(path, proj_type):
        name = os.path.basename(path)
        # If path is the root itself or empty name, use the folder name
        if not name:
            name = path
        found_projects.append({
            "name": name,
            "path": os.path.normpath(path),
            "type": proj_type
        })

    # Try loading C DLL
    if getattr(sys, 'frozen', False):
        # PyInstaller bundle directory
        dll_path = os.path.join(sys._MEIPASS, "core", "scanner.dll")
        if not os.path.exists(dll_path):
            dll_path = os.path.join(sys._MEIPASS, "scanner.dll")
    else:
        dll_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scanner.dll")
        if not os.path.exists(dll_path):
            # Check current folder as well
            dll_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scanner.dll")

    loaded_dll = False
    if os.path.exists(dll_path) and sys.platform == "win32":
        try:
            dll = ctypes.WinDLL(dll_path)
            # Define callback prototype
            # void (__stdcall *ProjectFoundCallback)(const wchar_t* path, const wchar_t* type)
            CALLBACK_TYPE = ctypes.WINFUNCTYPE(None, ctypes.c_wchar_p, ctypes.c_wchar_p)
            c_callback = CALLBACK_TYPE(on_project_found)

            dll.scan_projects.argtypes = [ctypes.c_wchar_p, ctypes.c_int, CALLBACK_TYPE]
            dll.scan_projects.restype = None

            # Call C function
            dll.scan_projects(root_path, max_depth, c_callback)
            loaded_dll = True
        except Exception as e:
            print(f"C DLL failed to load/execute, falling back to Python scan. Error: {e}")

    if not loaded_dll:
        # Run pure Python scan
        python_scan(root_path, 0, max_depth, on_project_found)

    # Sort projects by name
    found_projects.sort(key=lambda x: x["name"].lower())
    return found_projects
