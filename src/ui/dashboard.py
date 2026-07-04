import os
import customtkinter as ctk
from tkinter import filedialog, messagebox

# Core utilities
from core.scanner import scan_directory
from core.editors import detect_editors, open_in_editor
from core.runner import run_project, stop_project, get_running_projects, get_project_logs
from core.config import save_settings

class DashboardView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        
        # Grid layout (Header -> Search/Filter Bar -> Scrollable Project List)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.projects = []
        self.editor_options = {}  # {EditorName: Path}
        self.visible_count = 12   # Paginate projects to reduce RAM usage and prevent lagging
        
        self.create_header()
        self.create_filter_bar()
        self.create_projects_list_area()
        
        # Log viewer tracking
        self.active_log_window = None
        self.active_log_path = None

    def create_header(self):
        """Header area containing title and 'Create Project' / 'Rescan' buttons."""
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.header_frame.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(
            self.header_frame, 
            text="Project Dashboard", 
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_label.grid(row=0, column=0, sticky="w")

        # Action Buttons
        self.actions_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.actions_frame.grid(row=0, column=1, sticky="e")

        self.create_btn = ctk.CTkButton(
            self.actions_frame,
            text="➕ New Project",
            fg_color="#2ecc71",
            hover_color="#27ae60",
            text_color="white",
            font=ctk.CTkFont(weight="bold"),
            command=self.open_create_project_dialog
        )
        self.create_btn.grid(row=0, column=0, padx=5)

        self.rescan_btn = ctk.CTkButton(
            self.actions_frame,
            text="🔄 Scan Roots",
            command=self.scan_roots
        )
        self.rescan_btn.grid(row=0, column=1, padx=5)

    def create_filter_bar(self):
        """Filter bar for searching and filtering project list."""
        self.filter_frame = ctk.CTkFrame(self, height=50)
        self.filter_frame.grid(row=1, column=0, sticky="ew", pady=10)
        self.filter_frame.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            self.filter_frame, 
            placeholder_text="Search projects by name..."
        )
        self.search_entry.grid(row=0, column=0, padx=15, pady=10, sticky="ew")
        self.search_entry.bind("<KeyRelease>", self.filter_projects)

        # Dropdown to filter by type
        self.type_filter = ctk.CTkOptionMenu(
            self.filter_frame,
            values=["All Types", "Node.js", "Python", "Rust", "Go", "C/C++", "Java/Kotlin", "C#/.NET", "PHP", "Ruby", "HTML/CSS"],
            command=self.filter_projects
        )
        self.type_filter.grid(row=0, column=1, padx=(0, 15), pady=10)

    def create_projects_list_area(self):
        """Scrollable frame to render projects."""
        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.grid(row=2, column=0, sticky="nsew")
        self.scroll_frame.grid_columnconfigure(0, weight=1)

    def load_cached_projects(self):
        """Load projects from config cache. If empty, automatically scan."""
        self.editor_options = detect_editors()
        cached = self.controller.settings.get("cached_projects", None)
        
        # If cache is missing/empty, and root directories are defined, auto scan
        if cached is None:
            root_dirs = self.controller.settings.get("root_dirs", [])
            if root_dirs:
                self.scan_roots(silent=True)
                return
            else:
                self.projects = []
        else:
            self.projects = cached

        if not self.projects and not self.controller.settings.get("root_dirs", []):
            self.clear_project_cards()
            self.show_no_roots_warning()
            return

        self.filter_projects()

    def refresh_projects(self):
        """Interface method mapped to load_cached_projects."""
        self.load_cached_projects()

    def scan_roots(self, silent=False):
        """Perform full disk scan and update settings cache."""
        self.editor_options = detect_editors()
        root_dirs = self.controller.settings.get("root_dirs", [])
        
        if not root_dirs:
            self.clear_project_cards()
            self.show_no_roots_warning()
            return

        # Disable button during scan to indicate work
        self.rescan_btn.configure(state="disabled", text="Scanning...")
        self.update()

        try:
            scanned_projects = []
            for root in root_dirs:
                if os.path.exists(root):
                    scanned = scan_directory(root)
                    scanned_projects.extend(scanned)

            self.projects = scanned_projects
            self.controller.settings["cached_projects"] = self.projects
            save_settings(self.controller.settings)
            
            self.filter_projects()

            if not silent:
                messagebox.showinfo("Scan Complete", f"Scanned directories and found {len(self.projects)} projects.")
        finally:
            self.rescan_btn.configure(state="normal", text="🔄 Scan Roots")

    def add_project_to_cache(self, name, path):
        """Directly insert a project into cache to avoid full disk scan."""
        from core.scanner import PROJECT_SIGNATURES
        
        # Check files inside directory to match signature
        proj_type = "HTML/CSS"
        for sig, t in PROJECT_SIGNATURES.items():
            if os.path.exists(os.path.join(path, sig)):
                proj_type = t
                break
        
        new_proj = {
            "name": name,
            "path": os.path.normpath(path),
            "type": proj_type
        }

        # Prevent duplicate entries for the same path
        self.projects = [p for p in self.projects if p["path"] != new_proj["path"]]
        self.projects.append(new_proj)
        self.projects.sort(key=lambda x: x["name"].lower())

        self.controller.settings["cached_projects"] = self.projects
        save_settings(self.controller.settings)
        
        self.filter_projects()

    def clear_project_cards(self):
        """Destroy all current widgets in the scrollable list."""
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

    def show_no_roots_warning(self):
        """Show instructions to set up root directories."""
        warning_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        warning_frame.grid(row=0, column=0, pady=50, sticky="nsew")
        warning_frame.grid_columnconfigure(0, weight=1)

        warning_label = ctk.CTkLabel(
            warning_frame,
            text="No Root Folders Configured!\n\nTo scan your system for projects, please configure a root directory.",
            font=ctk.CTkFont(size=16)
        )
        warning_label.grid(row=0, column=0, pady=20)

        go_settings_btn = ctk.CTkButton(
            warning_frame,
            text="Go to Settings ⚙️",
            command=lambda: self.controller.select_frame_by_name("settings")
        )
        go_settings_btn.grid(row=1, column=0)

    def filter_projects(self, *args):
        """Re-render project cards matching search term and type filter."""
        if args:
            self.visible_count = 12

        self.clear_project_cards()

        search_term = self.search_entry.get().strip().lower()
        selected_type = self.type_filter.get()

        matched_projects = []
        for proj in self.projects:
            # Match search keyword
            if search_term and search_term not in proj["name"].lower():
                continue
            
            # Match type dropdown
            if selected_type != "All Types" and proj["type"] != selected_type:
                continue

            matched_projects.append(proj)

        # Slice list based on visible_count
        visible_projects = matched_projects[:self.visible_count]

        row = 0
        for proj in visible_projects:
            self.create_project_card(proj, row)
            row += 1

        # Render "Show More" button if there are more projects
        if len(matched_projects) > self.visible_count:
            remaining = len(matched_projects) - self.visible_count
            load_more_btn = ctk.CTkButton(
                self.scroll_frame,
                text=f"Show More Projects ({remaining} remaining) 🔽",
                height=35,
                command=self.load_more_projects,
                fg_color="gray30",
                hover_color="gray40"
            )
            load_more_btn.grid(row=row, column=0, pady=15, padx=5, sticky="ew")

        if len(matched_projects) == 0 and len(self.projects) > 0:
            no_results = ctk.CTkLabel(
                self.scroll_frame, 
                text="No projects match your search filters.", 
                font=ctk.CTkFont(size=14)
            )
            no_results.grid(row=0, column=0, pady=40)

    def load_more_projects(self):
        """Load next batch of projects to keep UI fast and lightweight."""
        self.visible_count += 12
        self.filter_projects()

    def create_project_card(self, proj, row):
        """Create a card container for a single project with optimized layout and widgets."""
        card = ctk.CTkFrame(self.scroll_frame, height=90)
        card.grid(row=row, column=0, sticky="ew", pady=6, padx=5)
        card.grid_columnconfigure(1, weight=1)
        card.grid_rowconfigure(0, weight=1)

        # Type indicator colors
        badge_colors = {
            "Node.js": ("#2ecc71", "#27ae60"),      # Green
            "Python": ("#3498db", "#2980b9"),       # Blue
            "Rust": ("#e67e22", "#d35400"),         # Orange
            "Go": ("#1abc9c", "#16a085"),           # Teal
            "C/C++": ("#e74c3c", "#c0392b"),        # Red
            "Java/Kotlin": ("#9b59b6", "#8e44ad"),  # Purple
            "C#/.NET": ("#1abc9c", "#16a085"),      # Cyan
            "PHP": ("#34495e", "#2c3e50"),          # Slate Blue
            "Ruby": ("#e74c3c", "#c0392b"),         # Red
            "HTML/CSS": ("#f1c40f", "#f39c12")      # Yellow/Gold
        }
        color = badge_colors.get(proj["type"], ("#7f8c8d", "#7f8c8d"))

        # Left Column: Project Type Badge (simplified layout without rowspan to prevent squishing)
        badge = ctk.CTkLabel(
            card,
            text=proj["type"].upper(),
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=color[0],
            text_color="white",
            corner_radius=4,
            width=80,
            height=24
        )
        badge.grid(row=0, column=0, padx=15, pady=20, sticky="w")

        # Center Column: Project Details (Name, Path)
        info_frame = ctk.CTkFrame(card, fg_color="transparent")
        info_frame.grid(row=0, column=1, sticky="w", pady=10)

        # Running status text if running
        running_projects = get_running_projects()
        is_running = proj["path"] in running_projects
        port_num = running_projects[proj["path"]]["port"] if is_running else None
        
        title_text = proj["name"]
        if is_running:
            title_text += f" (Running on Port {port_num})"

        # We remove explicit ("black", "white") to let CustomTkinter choose default visible colors automatically
        title_label = ctk.CTkLabel(
            info_frame,
            text=title_text,
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#3498db" if is_running else None
        )
        title_label.grid(row=0, column=0, sticky="w")

        path_label = ctk.CTkLabel(
            info_frame,
            text=proj["path"],
            font=ctk.CTkFont(size=11),
            text_color="gray60"
        )
        path_label.grid(row=1, column=0, sticky="w")

        # Right Column: Action Buttons Frame
        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.grid(row=0, column=2, padx=15, sticky="e")

        # 1. Editor Dropdown
        editors = list(self.editor_options.keys()) + list(self.controller.settings.get("custom_editors", {}).keys())
        default_choice = self.controller.settings.get("default_editor", "VS Code")
        if default_choice not in editors:
            editors.append(default_choice)

        editor_selector = ctk.CTkOptionMenu(
            btn_frame,
            values=editors,
            width=110,
            height=28
        )
        editor_selector.set(default_choice)
        editor_selector.grid(row=0, column=0, padx=4)

        # 2. Open Code button
        open_btn = ctk.CTkButton(
            btn_frame,
            text="💻 Open",
            width=70,
            height=28,
            command=lambda p=proj["path"], sel=editor_selector: self.launch_editor(p, sel.get())
        )
        open_btn.grid(row=0, column=1, padx=4)

        # 3. Run server button
        run_btn = ctk.CTkButton(
            btn_frame,
            text="⏹️ Stop" if is_running else "▶️ Run",
            fg_color="#e74c3c" if is_running else "#3498db",
            hover_color="#c0392b" if is_running else "#2980b9",
            width=70,
            height=28,
            command=lambda p=proj["path"], t=proj["type"]: self.toggle_project_run(p, t)
        )
        run_btn.grid(row=0, column=2, padx=4)

        # 4. View Log button (only enabled if project is running or logs exist)
        log_btn = ctk.CTkButton(
            btn_frame,
            text="📋 Logs",
            fg_color="gray30",
            hover_color="gray40",
            width=70,
            height=28,
            command=lambda p=proj["path"], n=proj["name"]: self.show_log_console(p, n)
        )
        log_btn.grid(row=0, column=3, padx=4)

    def launch_editor(self, path, selected_editor):
        """Lookup editor path and invoke opening logic."""
        exe_path = self.editor_options.get(selected_editor)
        if not exe_path:
            exe_path = self.controller.settings.get("custom_editors", {}).get(selected_editor)

        if not exe_path:
            messagebox.showerror("Error", f"Could not find install path for '{selected_editor}'. Configure it in settings.")
            return

        success, msg = open_in_editor(selected_editor, exe_path, path)
        if not success:
            messagebox.showerror("Error", msg)

    def toggle_project_run(self, path, proj_type):
        """Start or stop project background execution. Opens log console on startup error."""
        running = get_running_projects()
        name = os.path.basename(path)
        
        if path in running:
            # Stop it
            success, msg = stop_project(path)
            if success:
                self.refresh_projects()
            else:
                messagebox.showerror("Error", msg)
        else:
            # Start it (shows log window to indicate startup activity)
            self.show_log_console(path, name)
            
            success, msg, port = run_project(
                path, 
                proj_type, 
                log_callback=self.on_log_received
            )
            
            if success:
                self.refresh_projects()
            else:
                self.refresh_projects()
                messagebox.showerror("Error", f"Failed to start server:\n{msg}")

    def on_log_received(self, path, log_line):
        """Append log line to running console if matching active log path."""
        if self.active_log_window and self.active_log_path == path:
            try:
                self.log_textbox.configure(state="normal")
                self.log_textbox.insert("end", log_line)
                self.log_textbox.see("end")
                self.log_textbox.configure(state="disabled")
            except Exception:
                pass

    def show_log_console(self, path, name):
        """Display floating popup console for project logs."""
        self.active_log_path = path

        # If already open, raise window
        if self.active_log_window and self.active_log_window.winfo_exists():
            self.active_log_window.title(f"Logs: {name}")
            self.active_log_window.deiconify()
            self.active_log_window.focus()
            self.load_existing_logs(path)
            return

        # Create log window
        self.active_log_window = ctk.CTkToplevel(self)
        self.active_log_window.title(f"Logs: {name}")
        self.active_log_window.geometry("700x450")
        
        # Grid layout
        self.active_log_window.grid_rowconfigure(1, weight=1)
        self.active_log_window.grid_columnconfigure(0, weight=1)

        # Toolbar
        toolbar = ctk.CTkFrame(self.active_log_window, height=40)
        toolbar.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        
        title_lbl = ctk.CTkLabel(toolbar, text=f"Active Server Logs: {name}", font=ctk.CTkFont(weight="bold"))
        title_lbl.pack(side="left", padx=10)

        clear_btn = ctk.CTkButton(
            toolbar, 
            text="Clear", 
            width=60, 
            height=24,
            command=self.clear_console
        )
        clear_btn.pack(side="right", padx=5)

        # Text Console
        self.log_textbox = ctk.CTkTextbox(self.active_log_window, font=("Consolas", 12))
        self.log_textbox.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.log_textbox.configure(state="disabled")

        self.load_existing_logs(path)

    def load_existing_logs(self, path):
        """Fetch accumulated logs from runner cache."""
        logs = get_project_logs(path)
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.insert("end", logs)
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def clear_console(self):
        """Clear text console window and backend logs."""
        from core.runner import clear_project_logs
        if self.active_log_path:
            clear_project_logs(self.active_log_path)
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")

    def open_create_project_dialog(self):
        """Trigger modal popup for new project creation."""
        # Ensure we have a default root directory configured
        roots = self.controller.settings.get("root_dirs", [])
        if not roots:
            messagebox.showwarning("Warning", "Configure a root directory in settings before creating projects.")
            return

        # Modal dialog window
        dialog = ctk.CTkToplevel(self)
        dialog.title("Create New Project")
        dialog.geometry("450x320")
        dialog.resizable(False, False)
        dialog.transient(self) # Keep on top of main app
        dialog.grab_set()      # Block main app input

        # Layout
        dialog.grid_columnconfigure(1, weight=1)
        dialog.grid_rowconfigure(5, weight=1)

        # Title
        lbl = ctk.CTkLabel(dialog, text="Create Project Structure", font=ctk.CTkFont(size=16, weight="bold"))
        lbl.grid(row=0, column=0, columnspan=2, pady=15)

        # Name input
        name_lbl = ctk.CTkLabel(dialog, text="Project Name: ")
        name_lbl.grid(row=1, column=0, padx=20, pady=8, sticky="w")
        name_entry = ctk.CTkEntry(dialog, placeholder_text="my-new-project", width=250)
        name_entry.grid(row=1, column=1, padx=20, pady=8, sticky="ew")

        # Root directory select
        root_lbl = ctk.CTkLabel(dialog, text="Target Root: ")
        root_lbl.grid(row=2, column=0, padx=20, pady=8, sticky="w")
        
        root_selector = ctk.CTkOptionMenu(dialog, values=roots, width=250)
        root_selector.set(roots[0])
        root_selector.grid(row=2, column=1, padx=20, pady=8, sticky="ew")

        # Template selection
        temp_lbl = ctk.CTkLabel(dialog, text="Tech Template: ")
        temp_lbl.grid(row=3, column=0, padx=20, pady=8, sticky="w")
        
        temp_selector = ctk.CTkOptionMenu(
            dialog, 
            values=["Static HTML/CSS Page", "Node.js (Basic structure)", "Python (Simple App)"],
            width=250
        )
        temp_selector.grid(row=3, column=1, padx=20, pady=8, sticky="ew")

        # Action button
        def execute_create():
            proj_name = name_entry.get().strip()
            if not proj_name:
                messagebox.showerror("Error", "Project name cannot be empty.")
                return

            selected_root = root_selector.get()
            selected_template = temp_selector.get()
            target_dir = os.path.join(selected_root, proj_name)

            if os.path.exists(target_dir):
                messagebox.showerror("Error", "A directory with this name already exists in target root.")
                return

            try:
                # Create directories
                os.makedirs(target_dir, exist_ok=True)

                if "Static HTML/CSS" in selected_template:
                    self.scaffold_html_project(target_dir, proj_name)
                elif "Node.js" in selected_template:
                    self.scaffold_node_project(target_dir, proj_name)
                elif "Python" in selected_template:
                    self.scaffold_python_project(target_dir, proj_name)

                # Success, refresh dashboard
                dialog.destroy()
                self.add_project_to_cache(proj_name, target_dir)
                messagebox.showinfo("Success", f"Project '{proj_name}' created successfully!")
            except Exception as ex:
                messagebox.showerror("Error", f"Failed to create project folders: {ex}")

        submit_btn = ctk.CTkButton(
            dialog,
            text="🚀 Create Project",
            command=execute_create,
            fg_color="#2ecc71",
            hover_color="#27ae60"
        )
        submit_btn.grid(row=4, column=0, columnspan=2, pady=25)

    def scaffold_html_project(self, target_dir, name):
        """Create basic static site templates."""
        # index.html
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{name}</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="container">
        <h1>Welcome to {name}!</h1>
        <p>This boilerplate was automatically created by 🚀 <strong>DevHub</strong>.</p>
        <div id="date-display"></div>
    </div>
    <script src="script.js"></script>
</body>
</html>
"""
        with open(os.path.join(target_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(html_content)

        # style.css
        css_content = """body {
    margin: 0;
    padding: 0;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background-color: #1a1a2e;
    color: #ffffff;
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100vh;
}
.container {
    text-align: center;
    background-color: #162447;
    padding: 40px;
    border-radius: 12px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    border: 1px solid #0f4c75;
}
h1 {
    color: #3282b8;
    margin-bottom: 20px;
}
p {
    font-size: 1.1em;
    color: #bbe1fa;
}
"""
        with open(os.path.join(target_dir, "style.css"), "w", encoding="utf-8") as f:
            f.write(css_content)

        # script.js
        js_content = """document.addEventListener('DOMContentLoaded', () => {
    console.log('Project initialized.');
    const dateDiv = document.getElementById('date-display');
    if (dateDiv) {
        dateDiv.innerHTML = `<p>Created locally on: <strong>${new Date().toLocaleString()}</strong></p>`;
    }
});
"""
        with open(os.path.join(target_dir, "script.js"), "w", encoding="utf-8") as f:
            f.write(js_content)

    def scaffold_node_project(self, target_dir, name):
        """Create package.json and basic express server."""
        # package.json
        pkg_json = {
            "name": name.lower().replace(" ", "-"),
            "version": "1.0.0",
            "description": "Scaffolded Node project via DevHub",
            "main": "index.js",
            "scripts": {
                "start": "node index.js",
                "dev": "node index.js"
            },
            "dependencies": {}
        }
        with open(os.path.join(target_dir, "package.json"), "w", encoding="utf-8") as f:
            json.dump(pkg_json, f, indent=4)

        # index.js - basic HTTP server
        server_js = f"""const http = require('http');
const port = process.env.PORT || 3000;

const server = http.createServer((req, res) => {{
  res.statusCode = 200;
  res.setHeader('Content-Type', 'text/html');
  res.end('<h1>Welcome to {name} Node.js Server!</h1><p>Served successfully via DevHub.</p>');
}});

server.listen(port, () => {{
  console.log(`Server running at http://localhost:${{port}}/`);
}});
"""
        with open(os.path.join(target_dir, "index.js"), "w", encoding="utf-8") as f:
            f.write(server_js)

    def scaffold_python_project(self, target_dir, name):
        """Create standard Python entry app."""
        # app.py
        py_app = f"""# Python server script generated by DevHub
import http.server
import socketserver
import os

PORT = int(os.environ.get("PORT", 8000))

Handler = http.server.SimpleHTTPRequestHandler

# Create a basic landing page
with open("index.html", "w") as f:
    f.write(f'''<!DOCTYPE html>
<html>
<head><title>{name}</title></head>
<body style="background:#222;color:#fff;text-align:center;padding-top:100px;font-family:sans-serif;">
    <h1>Welcome to Python Web Server: {name}</h1>
    <p>Port configured: {PORT}</p>
</body>
</html>''')

print(f"Starting server on port {{PORT}}...")
with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Serving HTTP on 0.0.0.0 port {{PORT}} (http://127.0.0.1:{{PORT}}/) ...")
    httpd.serve_forever()
"""
        with open(os.path.join(target_dir, "app.py"), "w", encoding="utf-8") as f:
            f.write(py_app)

        # requirements.txt
        with open(os.path.join(target_dir, "requirements.txt"), "w", encoding="utf-8") as f:
            f.write("# Project dependencies\n")
