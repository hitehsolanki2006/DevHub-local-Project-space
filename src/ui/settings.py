import os
import customtkinter as ctk
from tkinter import filedialog, messagebox

# Core config utilities
from core.config import save_settings
from core.editors import detect_editors

class SettingsView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        
        # Grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1) # stretch bottom

        self.create_theme_section()
        self.create_roots_section()
        self.create_editors_section()

    def create_theme_section(self):
        """Create configuration panel for appearance theme."""
        theme_frame = ctk.CTkFrame(self)
        theme_frame.grid(row=0, column=0, sticky="ew", pady=10, padx=5)
        theme_frame.grid_columnconfigure(1, weight=1)

        lbl = ctk.CTkLabel(
            theme_frame, 
            text="App Theme Options", 
            font=ctk.CTkFont(size=14, weight="bold")
        )
        lbl.grid(row=0, column=0, columnspan=2, padx=15, pady=(10, 5), sticky="w")

        theme_lbl = ctk.CTkLabel(theme_frame, text="Select Theme:")
        theme_lbl.grid(row=1, column=0, padx=15, pady=10, sticky="w")

        self.theme_menu = ctk.CTkOptionMenu(
            theme_frame,
            values=["dark", "light", "system"],
            command=self.change_theme
        )
        self.theme_menu.grid(row=1, column=1, padx=15, pady=10, sticky="w")

    def create_roots_section(self):
        """Create panel to manage connected workspaces directory scan paths."""
        roots_frame = ctk.CTkFrame(self)
        roots_frame.grid(row=1, column=0, sticky="ew", pady=10, padx=5)
        roots_frame.grid_columnconfigure(0, weight=1)

        lbl = ctk.CTkLabel(
            roots_frame, 
            text="Connected Workspace Folders", 
            font=ctk.CTkFont(size=14, weight="bold")
        )
        lbl.grid(row=0, column=0, columnspan=2, padx=15, pady=(10, 5), sticky="w")

        # List box for folders (implemented as scrollable text box or text list)
        self.roots_textbox = ctk.CTkTextbox(roots_frame, height=100)
        self.roots_textbox.grid(row=1, column=0, padx=15, pady=10, sticky="ew")
        self.roots_textbox.configure(state="disabled")

        btn_group = ctk.CTkFrame(roots_frame, fg_color="transparent")
        btn_group.grid(row=1, column=1, padx=15, pady=10, sticky="ns")

        add_btn = ctk.CTkButton(
            btn_group, 
            text="➕ Add Folder", 
            width=120,
            command=self.add_root_directory
        )
        add_btn.grid(row=0, column=0, pady=5)

        clear_btn = ctk.CTkButton(
            btn_group, 
            text="❌ Clear All", 
            fg_color="#e74c3c",
            hover_color="#c0392b",
            width=120,
            command=self.clear_roots
        )
        clear_btn.grid(row=1, column=0, pady=5)

    def create_editors_section(self):
        """Panel to select default editor and register custom exe paths."""
        editors_frame = ctk.CTkFrame(self)
        editors_frame.grid(row=2, column=0, sticky="ew", pady=10, padx=5)
        editors_frame.grid_columnconfigure(1, weight=1)

        lbl = ctk.CTkLabel(
            editors_frame, 
            text="Editor Launcher Settings", 
            font=ctk.CTkFont(size=14, weight="bold")
        )
        lbl.grid(row=0, column=0, columnspan=3, padx=15, pady=(10, 5), sticky="w")

        # Default Editor Dropdown
        def_lbl = ctk.CTkLabel(editors_frame, text="Default Editor:")
        def_lbl.grid(row=1, column=0, padx=15, pady=10, sticky="w")

        self.editor_dropdown = ctk.CTkOptionMenu(
            editors_frame, 
            values=["VS Code"], # populated dynamically in load
            command=self.change_default_editor
        )
        self.editor_dropdown.grid(row=1, column=1, padx=15, pady=10, sticky="w")

        # Custom Editor Registrator
        custom_lbl = ctk.CTkLabel(
            editors_frame, 
            text="Add Custom Editor:",
            font=ctk.CTkFont(weight="bold")
        )
        custom_lbl.grid(row=2, column=0, padx=15, pady=(15, 5), sticky="w")

        self.custom_name_entry = ctk.CTkEntry(
            editors_frame, 
            placeholder_text="Editor Name (e.g. Sublime Text)"
        )
        self.custom_name_entry.grid(row=3, column=0, padx=15, pady=10, sticky="ew")

        self.custom_path_entry = ctk.CTkEntry(
            editors_frame, 
            placeholder_text="Executable Path (.exe)"
        )
        self.custom_path_entry.grid(row=3, column=1, padx=15, pady=10, sticky="ew")

        browse_btn = ctk.CTkButton(
            editors_frame, 
            text="Browse Exe", 
            width=100, 
            command=self.browse_custom_exe
        )
        browse_btn.grid(row=3, column=2, padx=15, pady=10)

        register_btn = ctk.CTkButton(
            editors_frame, 
            text="Register Editor", 
            command=self.register_custom_editor
        )
        register_btn.grid(row=4, column=0, columnspan=3, pady=(5, 15))

    def load_current_configs(self):
        """Populate controls with current settings from local disk."""
        settings = self.controller.settings
        
        # Load theme setting
        self.theme_menu.set(settings.get("theme", "dark"))

        # Load roots list
        self.roots_textbox.configure(state="normal")
        self.roots_textbox.delete("1.0", "end")
        
        roots = settings.get("root_dirs", [])
        if roots:
            for root in roots:
                self.roots_textbox.insert("end", f"{root}\n")
        else:
            self.roots_textbox.insert("end", "(No roots configured)")
            
        self.roots_textbox.configure(state="disabled")

        # Load editor dropdown options
        detected = list(detect_editors().keys())
        custom = list(settings.get("custom_editors", {}).keys())
        all_editors = list(set(detected + custom))
        
        if not all_editors:
            all_editors = ["VS Code"] # default fallback
            
        self.editor_dropdown.configure(values=all_editors)
        
        current_default = settings.get("default_editor", "VS Code")
        if current_default in all_editors:
            self.editor_dropdown.set(current_default)
        else:
            self.editor_dropdown.set(all_editors[0])

    def change_theme(self, selection):
        """Invoke theme controller update."""
        self.controller.update_theme(selection)

    def add_root_directory(self):
        """Prompt directory picker and save path in settings."""
        directory = filedialog.askdirectory(title="Select Projects Root Folder")
        if directory:
            directory = os.path.normpath(directory)
            current_roots = self.controller.settings.get("root_dirs", [])
            
            if directory in current_roots:
                messagebox.showinfo("Info", "Directory is already added.")
                return

            current_roots.append(directory)
            self.controller.settings["root_dirs"] = current_roots
            save_settings(self.controller.settings)
            
            self.load_current_configs()
            messagebox.showinfo("Success", "Workspace directory connected.")

    def clear_roots(self):
        """Erase all active workspaces from scan list."""
        if messagebox.askyesno("Confirm Clear", "Are you sure you want to disconnect all root folders?"):
            self.controller.settings["root_dirs"] = []
            save_settings(self.controller.settings)
            self.load_current_configs()

    def change_default_editor(self, selection):
        """Update default editor configuration."""
        self.controller.settings["default_editor"] = selection
        save_settings(self.controller.settings)

    def browse_custom_exe(self):
        """Open file picker to select a custom text editor .exe path."""
        file_path = filedialog.askopenfilename(
            title="Select Editor Executable (.exe)",
            filetypes=[("Executable Files", "*.exe")]
        )
        if file_path:
            self.custom_path_entry.delete(0, "end")
            self.custom_path_entry.insert(0, os.path.normpath(file_path))

    def register_custom_editor(self):
        """Verify and save custom editor path to local database."""
        name = self.custom_name_entry.get().strip()
        path = self.custom_path_entry.get().strip()

        if not name or not path:
            messagebox.showerror("Error", "Please fill in both the Editor Name and Executable Path.")
            return

        if not os.path.exists(path):
            messagebox.showerror("Error", "The executable path provided does not exist.")
            return

        custom_editors = self.controller.settings.get("custom_editors", {})
        custom_editors[name] = os.path.normpath(path)
        
        self.controller.settings["custom_editors"] = custom_editors
        # Auto-set as default editor
        self.controller.settings["default_editor"] = name
        
        save_settings(self.controller.settings)

        # Clear inputs
        self.custom_name_entry.delete(0, "end")
        self.custom_path_entry.delete(0, "end")

        self.load_current_configs()
        messagebox.showinfo("Success", f"Custom editor '{name}' registered and set as default.")
