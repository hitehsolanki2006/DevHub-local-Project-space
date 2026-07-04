# 🚀 DevHub: High-Performance Desktop Project Launcher

DevHub is a lightweight, blazing-fast desktop application designed to organize, open, run, and clone your local development projects from one unified workspace dashboard. It connects to local project directories, auto-detects installed code editors, manages background dev runners, and integrates with GitHub.

Developed using a **hybrid Python + C architecture**, it combines high-level GUI flexibility with low-level Windows registry queries and file system scans at hardware speeds.

---

## 🌟 Key Features

1. **Workspace Scanning & Indexing**: Detects project roots (Node.js, Python, Rust, Go, Static Web) by scanning configurations recursively. Uses a fast native C DLL with the Windows Win32 API.
2. **Editor Integration**: Automatically reads the Windows registry to locate installed editors (VS Code, Cursor, Notepad++, Sublime Text) and launch them with a single click. Custom executable paths can also be added.
3. **Smart Server Runner**: Spawns background dev servers (e.g. `npm run dev`, `python app.py`) in independent threads. It auto-detects busy ports, increments to find a free one, and displays live log outputs in a floating terminal console. Clean process termination prevents locked ports.
4. **GitHub Repo Manager**: Pulls repository listings from your GitHub account. Clones public and private repos directly to your connected workspace root in background threads, immediately indexing them when complete.
5. **Project Creator Boilerplate**: Creates new project directories from templates (Vanilla HTML/CSS, Node.js Server, Python Script) and launches them instantly.

---

## 🛠️ Tech Stack & Architecture

- **GUI & Application Core**: Python 3.10+ & [CustomTkinter](https://github.com/TomSchimansky/Customtkinter) (modern dark-themed Tkinter layout).
- **Fast Search Engine**: C (`scanner.c`) utilizing Windows native Win32 `FindFirstFileW` & `FindNextFileW` for scanning, loaded in Python via `ctypes`.
- **Pure Python Fallback**: If the compiled `scanner.dll` is not present (e.g. during local testing), DevHub automatically falls back to Python's built-in `os.scandir` and `winreg` modules so it runs out-of-the-box.
- **CI/CD Pipeline**: GitHub Actions compiles the C code and bundles a single-file executable `DevHub.exe` automatically on push.

---

## 🚀 How to Run Locally (Testing)

No compiler is needed to test locally. You only need a standard Python installation:

1. **Navigate to the Project Folder**:
   ```bash
   cd "D:\My projects\DevHub"
   ```

2. **Create & Activate a Virtual Environment** (Optional but recommended):
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Launch DevHub**:
   ```bash
   python src/main.py
   ```

---

## 📦 How to Build the Standalone `.exe`

The build process is fully automated via GitHub Actions, but you can also compile it locally if you have a C compiler installed:

### Automatic (GitHub Actions)
1. Initialize your GitHub remote repository and push this codebase.
2. On your GitHub Repository page, navigate to the **Actions** tab.
3. Once the workflow finishes, click on the run and download the `DevHub-Windows-Build` ZIP file from the **Artifacts** section at the bottom.

### Manual Local Build (Requires MSVC Compiler)
If you have MSVC installed (via Visual Studio Build Tools) and PyInstaller installed:
```bash
# 1. Compile C Scanner DLL
cl.exe /LD /O2 src/c_core/scanner.c /Fe:src/scanner.dll

# 2. Package into one-file .exe
pyinstaller --noconsole --onefile --add-data "src/scanner.dll;core" --name "DevHub" src/main.py
```
The compiled executable will be located in the `dist/` directory as `DevHub.exe`.
