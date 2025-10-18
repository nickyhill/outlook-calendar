import subprocess
import sys

def kill_leftover_chrome():
    try:
        # # Kill any running chromedriver processes
        success = subprocess.run(["pkill", "-f", "chromedriver"], capture_output=True, shell=True)
        # # Optionally kill any Chrome instances started by Selenium
        success_second = subprocess.run(["pkill", "-f", "chrome"], capture_output=True, shell=True)
        final = subprocess.run(["kill", "-9", "$(sudo lsof -t -i:9222)"], capture_output=True, shell=True)

        print(f"Killed leftover Chrome driver processes: {success.stdout}")
        print(f"Killed leftover Chrome processes: {success_second.stdout}")
        print(f"Killed leftover :9222 processes: {final.stdout}")

    except Exception as e:
        print(f"Failed to kill leftover Chrome processes: {e}", file=sys.stderr)

