import os
import customtkinter as ctk
from PIL import Image
from tkinter import filedialog, messagebox
from core.editors import detect_editors

# Import core modules
from core.config import load_settings, save_settings
# Import views (which we will create next)
from ui.dashboard import DashboardView
from ui.settings import SettingsView
from ui.github_view import GitHubView

class DevHubApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Load application configurations
        self.settings = load_settings()
        
        # Setup Window Properties
        self.title("DevHub - Local Workspace Dashboard")
        self.geometry("1100x700")
        self.minimum_width = 850
        self.minimum_height = 550
        self.minsize(self.minimum_width, self.minimum_height)
        
        # Set theme and styling
        ctk.set_appearance_mode(self.settings.get("theme", "dark"))
        ctk.set_default_color_theme("blue")
        
        # Set grid layout 1x2 (Sidebar + Main View Content)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Create Navigation Sidebar
        self.create_sidebar()

        # Create Container Frame for active views
        self.container_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.container_frame.grid(row=0, column=1, sticky="nsew", padx=15, pady=15)
        self.container_frame.grid_rowconfigure(0, weight=1)
        self.container_frame.grid_columnconfigure(0, weight=1)

        # Initialize Views
        self.views = {}
        self.views["dashboard"] = DashboardView(self.container_frame, self)
        self.views["github"] = GitHubView(self.container_frame, self)
        self.views["settings"] = SettingsView(self.container_frame, self)

        # Position all views in the same grid cell (they overlap, we raise the active one)
        for view_name, view_instance in self.views.items():
            view_instance.grid(row=0, column=0, sticky="nsew")

        # Start with dashboard
        self.select_frame_by_name("dashboard")

        # Check for first-run onboarding
        if self.settings.get("first_run", True):
            self.after(200, self.show_onboarding_dialog)

    def show_onboarding_dialog(self):
        """Displays a modal dialog on first run to setup Workspace Root and Default Editor."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("DevHub Setup Wizard")
        dialog.geometry("520x460")
        dialog.resizable(False, False)
        dialog.transient(self) # Keep on top of main app
        dialog.grab_set()      # Block input to main app

        # Layout configure
        dialog.grid_columnconfigure(0, weight=1)

        # Header Title
        title_lbl = ctk.CTkLabel(
            dialog, 
            text="Welcome to DevHub! 🚀", 
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_lbl.pack(pady=(20, 5))

        desc_lbl = ctk.CTkLabel(
            dialog, 
            text="Let's complete a quick first-time setup to get started.",
            font=ctk.CTkFont(size=13),
            text_color="gray60"
        )
        desc_lbl.pack(pady=(0, 20))

        # --- STEP 1: Workspace Folder ---
        ws_frame = ctk.CTkFrame(dialog)
        ws_frame.pack(fill="x", padx=30, pady=10)

        ws_title = ctk.CTkLabel(
            ws_frame, 
            text="1. Connect Projects Folder (Workspace Root)", 
            font=ctk.CTkFont(weight="bold")
        )
        ws_title.pack(anchor="w", padx=15, pady=(10, 5))

        ws_input_frame = ctk.CTkFrame(ws_frame, fg_color="transparent")
        ws_input_frame.pack(fill="x", padx=15, pady=(0, 10))

        ws_entry = ctk.CTkEntry(
            ws_input_frame, 
            placeholder_text="e.g. D:\\My projects", 
            height=28
        )
        ws_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        def browse_workspace():
            folder = filedialog.askdirectory(title="Select Projects Root Folder")
            if folder:
                ws_entry.delete(0, "end")
                ws_entry.insert(0, os.path.normpath(folder))

        ws_btn = ctk.CTkButton(ws_input_frame, text="Browse", width=70, height=28, command=browse_workspace)
        ws_btn.pack(side="right")

        # --- STEP 2: Code Editor Setup ---
        ed_frame = ctk.CTkFrame(dialog)
        ed_frame.pack(fill="x", padx=30, pady=10)

        ed_title = ctk.CTkLabel(
            ed_frame, 
            text="2. Configure Code Editor", 
            font=ctk.CTkFont(weight="bold")
        )
        ed_title.pack(anchor="w", padx=15, pady=(10, 5))

        # Detect editors
        detected_editors = detect_editors()
        editor_names = list(detected_editors.keys())
        
        select_lbl = ctk.CTkLabel(ed_frame, text="Select Preferred Editor:")
        select_lbl.pack(anchor="w", padx=15)

        selector_frame = ctk.CTkFrame(ed_frame, fg_color="transparent")
        selector_frame.pack(fill="x", padx=15, pady=(0, 5))

        # Editor option menu
        menu_values = editor_names + ["Custom Editor Path..."] if editor_names else ["Custom Editor Path..."]
        ed_option = ctk.CTkOptionMenu(selector_frame, values=menu_values, height=28)
        ed_option.pack(side="left", fill="x", expand=True, padx=(0, 10))
        if editor_names:
            ed_option.set(editor_names[0])
        else:
            ed_option.set("Custom Editor Path...")

        # Custom Editor inputs
        custom_input_frame = ctk.CTkFrame(ed_frame, fg_color="transparent")
        
        custom_name_entry = ctk.CTkEntry(
            custom_input_frame, 
            placeholder_text="Editor Name (e.g. Cursor)", 
            height=28
        )
        custom_name_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        custom_path_entry = ctk.CTkEntry(
            custom_input_frame, 
            placeholder_text="Executable Path (.exe)", 
            height=28
        )
        custom_path_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        def browse_custom_exe():
            file_path = filedialog.askopenfilename(
                title="Select Editor Executable (.exe)",
                filetypes=[("Executable Files", "*.exe")]
            )
            if file_path:
                custom_path_entry.delete(0, "end")
                custom_path_entry.insert(0, os.path.normpath(file_path))

        custom_browse_btn = ctk.CTkButton(
            custom_input_frame, 
            text="Browse Exe", 
            width=80, 
            height=28, 
            command=browse_custom_exe
        )
        custom_browse_btn.pack(side="right")

        def on_editor_selection_changed(choice):
            if choice == "Custom Editor Path...":
                custom_input_frame.pack(fill="x", padx=15, pady=(5, 10))
            else:
                custom_input_frame.pack_forget()

        ed_option.configure(command=on_editor_selection_changed)

        # Trigger initial state of custom inputs
        on_editor_selection_changed(ed_option.get())

        # --- STEP 3: Complete ---
        def complete_onboarding():
            ws_path = ws_entry.get().strip()
            if not ws_path:
                messagebox.showerror("Error", "Please select a projects root folder.")
                return
            if not os.path.exists(ws_path):
                messagebox.showerror("Error", "The projects root folder directory does not exist.")
                return

            selected_choice = ed_option.get()
            final_editor_name = selected_choice
            custom_editor_path = None

            if selected_choice == "Custom Editor Path...":
                final_editor_name = custom_name_entry.get().strip()
                custom_editor_path = custom_path_entry.get().strip()

                if not final_editor_name or not custom_editor_path:
                    messagebox.showerror("Error", "Please fill in both custom editor Name and Path.")
                    return
                if not os.path.exists(custom_editor_path):
                    messagebox.showerror("Error", "The custom editor executable path does not exist.")
                    return

            # Save configurations
            self.settings["root_dirs"] = [os.path.normpath(ws_path)]
            self.settings["default_editor"] = final_editor_name
            self.settings["first_run"] = False

            if custom_editor_path:
                custom_map = self.settings.get("custom_editors", {})
                custom_map[final_editor_name] = os.path.normpath(custom_editor_path)
                self.settings["custom_editors"] = custom_map

            save_settings(self.settings)

            # Close onboarding and reload dashboard
            dialog.destroy()
            self.views["dashboard"].scan_roots(silent=True)
            messagebox.showinfo("Setup Complete", "Welcome to DevHub! Your workspace is fully set up.")

        finish_btn = ctk.CTkButton(
            dialog, 
            text="🚀 Finish Setup", 
            font=ctk.CTkFont(weight="bold"), 
            height=36,
            fg_color="#2ecc71",
            hover_color="#27ae60",
            command=complete_onboarding
        )
        finish_btn.pack(pady=(20, 15))

    def create_sidebar(self):
        """Create navigation sidebar frame."""
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1) # spacer row

        # App Logo / Title
        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text="🚀 DevHub", 
            font=ctk.CTkFont(size=22, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(25, 25))

        # Navigation Buttons
        self.dash_button = ctk.CTkButton(
            self.sidebar_frame, 
            text="📁  Projects", 
            height=40,
            corner_radius=8,
            border_spacing=10,
            anchor="w",
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            font=ctk.CTkFont(size=14),
            command=lambda: self.select_frame_by_name("dashboard")
        )
        self.dash_button.grid(row=1, column=0, padx=15, pady=5, sticky="ew")

        self.github_button = ctk.CTkButton(
            self.sidebar_frame, 
            text="🐙  GitHub Repos", 
            height=40,
            corner_radius=8,
            border_spacing=10,
            anchor="w",
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            font=ctk.CTkFont(size=14),
            command=lambda: self.select_frame_by_name("github")
        )
        self.github_button.grid(row=2, column=0, padx=15, pady=5, sticky="ew")

        self.settings_button = ctk.CTkButton(
            self.sidebar_frame, 
            text="⚙️  Settings", 
            height=40,
            corner_radius=8,
            border_spacing=10,
            anchor="w",
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            font=ctk.CTkFont(size=14),
            command=lambda: self.select_frame_by_name("settings")
        )
        self.settings_button.grid(row=3, column=0, padx=15, pady=5, sticky="ew")

        # Footer info
        self.info_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text="v1.0.0 (Python+C)", 
            font=ctk.CTkFont(size=11), 
            text_color="gray50"
        )
        self.info_label.grid(row=5, column=0, pady=15)

    def select_frame_by_name(self, name):
        """Toggle frame visibility and highlight sidebar buttons."""
        # Reset button styles
        self.dash_button.configure(fg_color="transparent")
        self.github_button.configure(fg_color="transparent")
        self.settings_button.configure(fg_color="transparent")

        # Highlight active button
        if name == "dashboard":
            self.dash_button.configure(fg_color=("gray75", "gray25"))
            self.views["dashboard"].load_cached_projects() # Load cached projects instead of scanning every time!
        elif name == "github":
            self.github_button.configure(fg_color=("gray75", "gray25"))
            self.views["github"].load_repositories()
        elif name == "settings":
            self.settings_button.configure(fg_color=("gray75", "gray25"))
            self.views["settings"].load_current_configs()

        # Show active view
        self.views[name].tkraise()

    def update_theme(self, theme_name):
        """Update active window theme dynamically."""
        self.settings["theme"] = theme_name
        save_settings(self.settings)
        ctk.set_appearance_mode(theme_name)
