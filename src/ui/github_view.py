import os
import customtkinter as ctk
import requests
import threading
import subprocess
from tkinter import filedialog, messagebox

# Core config utilities
from core.config import save_settings

class GitHubView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        
        # Grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1) # stretch repository list area

        self.repositories = []
        
        self.create_auth_panel()
        self.create_search_bar()
        self.create_repo_list_area()

    def create_auth_panel(self):
        """Credentials layout area."""
        self.auth_frame = ctk.CTkFrame(self)
        self.auth_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10), padx=5)
        
        # Grid layout inside auth panel
        self.auth_frame.grid_columnconfigure(1, weight=1)
        self.auth_frame.grid_columnconfigure(3, weight=1)

        lbl = ctk.CTkLabel(
            self.auth_frame, 
            text="GitHub Account Integration", 
            font=ctk.CTkFont(size=14, weight="bold")
        )
        lbl.grid(row=0, column=0, columnspan=5, padx=15, pady=(10, 5), sticky="w")

        # Username Input
        user_lbl = ctk.CTkLabel(self.auth_frame, text="Username:")
        user_lbl.grid(row=1, column=0, padx=(15, 5), pady=10, sticky="w")
        
        self.user_entry = ctk.CTkEntry(self.auth_frame, placeholder_text="github-username")
        self.user_entry.grid(row=1, column=1, padx=5, pady=10, sticky="ew")

        # PAT Token Input
        token_lbl = ctk.CTkLabel(self.auth_frame, text="Personal Access Token (PAT):")
        token_lbl.grid(row=1, column=2, padx=(15, 5), pady=10, sticky="w")
        
        self.token_entry = ctk.CTkEntry(
            self.auth_frame, 
            placeholder_text="ghp_xxxxxxxxxxxxxxxxxxxx", 
            show="*"
        )
        self.token_entry.grid(row=1, column=3, padx=5, pady=10, sticky="ew")

        # Save Button
        save_btn = ctk.CTkButton(
            self.auth_frame, 
            text="💾 Save & Connect", 
            width=110,
            command=self.save_github_credentials
        )
        save_btn.grid(row=1, column=4, padx=15, pady=10)

    def create_search_bar(self):
        """Filtering repositories bar."""
        self.filter_frame = ctk.CTkFrame(self, height=45)
        self.filter_frame.grid(row=1, column=0, sticky="ew", pady=5, padx=5)
        self.filter_frame.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            self.filter_frame, 
            placeholder_text="Filter remote repositories by name..."
        )
        self.search_entry.grid(row=0, column=0, padx=15, pady=8, sticky="ew")
        self.search_entry.bind("<KeyRelease>", self.filter_repos)

        self.fetch_btn = ctk.CTkButton(
            self.filter_frame,
            text="🔄 Fetch Repos",
            width=100,
            command=self.load_repositories
        )
        self.fetch_btn.grid(row=0, column=1, padx=15, pady=8)

    def create_repo_list_area(self):
        """Scrollable frame to render repositories."""
        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=10)
        self.scroll_frame.grid_columnconfigure(0, weight=1)

    def save_github_credentials(self):
        """Persist username and token in settings file."""
        username = self.user_entry.get().strip()
        token = self.token_entry.get().strip()

        self.controller.settings["github_username"] = username
        self.controller.settings["github_token"] = token
        
        save_settings(self.controller.settings)
        messagebox.showinfo("Success", "GitHub credentials saved. Fetching repository list...")
        self.load_repositories()

    def load_current_configs(self):
        """Pre-populate entry fields on load."""
        username = self.controller.settings.get("github_username", "")
        token = self.controller.settings.get("github_token", "")

        self.user_entry.delete(0, "end")
        self.user_entry.insert(0, username)

        self.token_entry.delete(0, "end")
        self.token_entry.insert(0, token)

    def load_repositories(self):
        """Fetch repositories from GitHub API in a background thread."""
        self.load_current_configs()
        
        username = self.user_entry.get().strip()
        token = self.token_entry.get().strip()

        if not username:
            self.clear_repo_cards()
            no_user_lbl = ctk.CTkLabel(
                self.scroll_frame, 
                text="Please configure your GitHub username above to fetch repositories.", 
                font=ctk.CTkFont(size=14)
            )
            no_user_lbl.grid(row=0, column=0, pady=40)
            return

        # Show Loading status
        self.clear_repo_cards()
        loading_lbl = ctk.CTkLabel(
            self.scroll_frame, 
            text="Connecting to GitHub API... Please wait.", 
            font=ctk.CTkFont(size=14)
        )
        loading_lbl.grid(row=0, column=0, pady=40)

        # Threaded call to prevent UI freezing
        t = threading.Thread(target=self._fetch_repos_thread, args=(username, token), daemon=True)
        t.start()

    def _fetch_repos_thread(self, username, token):
        """Background worker thread to run HTTP API query."""
        repos = []
        try:
            headers = {}
            if token:
                headers["Authorization"] = f"token {token}"
            
            # If token is present, we get private + public repos from 'user/repos'
            # Otherwise public repos only from 'users/username/repos'
            if token:
                url = "https://api.github.com/user/repos?per_page=100&sort=updated"
            else:
                url = f"https://api.github.com/users/{username}/repos?per_page=100&sort=updated"

            response = requests.get(url, headers=headers, timeout=15)

            if response.status_code == 200:
                data = response.json()
                for item in data:
                    repos.append({
                        "name": item.get("name"),
                        "fullname": item.get("full_name"),
                        "description": item.get("description", "No description provided."),
                        "clone_url": item.get("clone_url"),
                        "ssh_url": item.get("ssh_url"),
                        "private": item.get("private", False),
                        "language": item.get("language", "Unknown")
                    })
                self.repositories = repos
                self.controller.after(0, self.filter_repos)
            else:
                err_msg = response.json().get("message", "Request failed.")
                self.controller.after(0, lambda: self.show_error_message(f"GitHub Error: {err_msg}"))
        except Exception as e:
            self.controller.after(0, lambda: self.show_error_message(f"Failed to connect to GitHub: {e}"))

    def show_error_message(self, message):
        """Callback to handle error alerts in UI main thread."""
        self.clear_repo_cards()
        err_lbl = ctk.CTkLabel(self.scroll_frame, text=message, font=ctk.CTkFont(size=13), text_color="#e74c3c")
        err_lbl.grid(row=0, column=0, pady=40)

    def clear_repo_cards(self):
        """Wipe card widgets."""
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

    def filter_repos(self, *args):
        """Redraw repo lists matching query search keyword."""
        self.clear_repo_cards()
        search_term = self.search_entry.get().strip().lower()

        row = 0
        for repo in self.repositories:
            if search_term and search_term not in repo["name"].lower():
                continue
            self.create_repo_card(repo, row)
            row += 1

        if row == 0 and len(self.repositories) > 0:
            no_results = ctk.CTkLabel(self.scroll_frame, text="No repositories match your search filter.")
            no_results.grid(row=0, column=0, pady=40)
        elif len(self.repositories) == 0:
            no_repos = ctk.CTkLabel(self.scroll_frame, text="No repositories found for this account.")
            no_repos.grid(row=0, column=0, pady=40)

    def create_repo_card(self, repo, row):
        """Render a single Git repo representation card."""
        card = ctk.CTkFrame(self.scroll_frame, height=85)
        card.grid(row=row, column=0, sticky="ew", pady=6, padx=5)
        card.grid_columnconfigure(1, weight=1)

        # Left Visibility Badge (Public / Private)
        badge_text = "🔒 Private" if repo["private"] else "🌐 Public"
        badge_color = ("#e74c3c", "#c0392b") if repo["private"] else ("#27ae60", "#2196f3")
        
        badge = ctk.CTkLabel(
            card,
            text=badge_text,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=badge_color[0],
            text_color="white",
            corner_radius=4,
            width=70,
            height=24
        )
        badge.grid(row=0, column=0, rowspan=2, padx=15, pady=15)

        # Center Description Info
        info_frame = ctk.CTkFrame(card, fg_color="transparent")
        info_frame.grid(row=0, column=1, rowspan=2, sticky="w", pady=10)

        # Truncate description if too long
        desc = repo["description"]
        if desc and len(desc) > 85:
            desc = desc[:82] + "..."

        title_lbl = ctk.CTkLabel(
            info_frame, 
            text=f"{repo['name']}   •   {repo['language']}", 
            font=ctk.CTkFont(size=15, weight="bold")
        )
        title_lbl.grid(row=0, column=0, sticky="w")

        desc_lbl = ctk.CTkLabel(
            info_frame, 
            text=desc or "No description.", 
            font=ctk.CTkFont(size=11), 
            text_color="gray60"
        )
        desc_lbl.grid(row=1, column=0, sticky="w")

        # Right Action: Clone Button
        clone_btn = ctk.CTkButton(
            card,
            text="⬇️ Clone",
            width=90,
            command=lambda r=repo: self.initiate_clone(r)
        )
        clone_btn.grid(row=0, column=2, rowspan=2, padx=20, sticky="e")

    def initiate_clone(self, repo):
        """Prompt root select and trigger background clone thread."""
        roots = self.controller.settings.get("root_dirs", [])
        if not roots:
            messagebox.showwarning("Warning", "Configure a workspace root folder in settings before cloning repositories.")
            return

        # Simple prompt asking user to select target root folder if multiple exist
        target_root = roots[0]
        if len(roots) > 1:
            # Let them select via folder picker or simple dialog (we'll open dialog for flexibility)
            dialog = ctk.CTkToplevel(self)
            dialog.title("Select Target Root")
            dialog.geometry("380x180")
            dialog.resizable(False, False)
            dialog.transient(self)
            dialog.grab_set()

            dialog.grid_columnconfigure(0, weight=1)

            lbl = ctk.CTkLabel(
                dialog, 
                text=f"Clone '{repo['name']}' to which root folder?", 
                font=ctk.CTkFont(weight="bold")
            )
            lbl.pack(pady=15)

            selector = ctk.CTkOptionMenu(dialog, values=roots, width=280)
            selector.pack(pady=10)

            def select_and_close():
                nonlocal target_root
                target_root = selector.get()
                dialog.destroy()
                self._start_clone_process(repo, target_root)

            btn = ctk.CTkButton(dialog, text="Clone Here", command=select_and_close)
            btn.pack(pady=15)
        else:
            self._start_clone_process(repo, target_root)

    def _start_clone_process(self, repo, target_root):
        """Create target clone folders and invoke background worker thread."""
        target_path = os.path.join(target_root, repo["name"])
        
        if os.path.exists(target_path):
            messagebox.showerror("Error", f"Folder '{repo['name']}' already exists in selected root directory.")
            return

        messagebox.showinfo("Clone Started", f"Cloning '{repo['name']}' in the background. We will notify you when done.")
        
        # Threaded clone
        t = threading.Thread(
            target=self._git_clone_worker, 
            args=(repo["clone_url"], target_path, repo["name"]), 
            daemon=True
        )
        t.start()

    def _git_clone_worker(self, url, path, name):
        """Launch git clone shell processes and notify GUI on status changes."""
        try:
            # If user has a token, inject it in the URL for authenticated private cloning
            token = self.controller.settings.get("github_token", "")
            username = self.controller.settings.get("github_username", "")
            
            clone_url = url
            if token and username in url:
                # Replace 'https://github.com/' with 'https://<username>:<token>@github.com/'
                clone_url = url.replace("https://github.com/", f"https://{username}:{token}@github.com/")

            # Detached process to hide shell on Windows
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            result = subprocess.run(
                ["git", "clone", clone_url, path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo
            )

            if result.returncode == 0:
                self.controller.after(0, lambda: messagebox.showinfo(
                    "Clone Complete", 
                    f"Successfully cloned repository '{name}'!\nIt is now indexed on the Dashboard."
                ))
            else:
                err_msg = result.stderr.decode("utf-8", errors="replace")
                self.controller.after(0, lambda: messagebox.showerror(
                    "Clone Failed", 
                    f"Failed to clone '{name}':\n{err_msg}"
                ))
        except Exception as e:
            self.controller.after(0, lambda: messagebox.showerror(
                "Clone Failed", 
                f"An unexpected error occurred during cloning:\n{e}"
            ))
