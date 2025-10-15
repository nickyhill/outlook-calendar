import subprocess
import sys

def kill_leftover_chrome():
    try:
        # Kill any running chromedriver processes
        subprocess.run(["pkill", "-f", "chromedriver"], capture_output=True)
        # Optionally kill any Chrome instances started by Selenium
        subprocess.run(["pkill", "-f", "chrome"], capture_output=True)

        subprocess.run(["kill", "-9", "$(sudo lsof -t -i:9222)"], capture_output=True)

    except Exception as e:
        print(f"Failed to kill leftover Chrome processes: {e}", file=sys.stderr)

