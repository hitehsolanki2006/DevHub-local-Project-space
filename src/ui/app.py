import os
import customtkinter as ctk
from PIL import Image

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
