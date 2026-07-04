import os
import sys

# Add the 'src' directory to python path to allow clean imports
src_dir = os.path.dirname(os.path.abspath(__file__))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from ui.app import DevHubApp

def main():
    try:
        app = DevHubApp()
        app.mainloop()
    except Exception as e:
        import traceback
        # Save crash log for debug
        crash_log = os.path.join(os.path.dirname(src_dir), "crash_log.txt")
        with open(crash_log, "w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        print(f"Application crashed. Traceback saved to {crash_log}")
        raise e

if __name__ == "__main__":
    main()
