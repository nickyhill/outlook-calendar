import subprocess
import sys

def kill_leftover_chrome():
    try:
        # Kill any running chromedriver processes
        subprocess.run("pkill -f chromedriver", check=False)
        # Optionally kill any Chrome instances started by Selenium
        subprocess.run("pkill -f chrome", check=False)
    except Exception as e:
        print(f"Failed to kill leftover Chrome processes: {e}", file=sys.stderr)
