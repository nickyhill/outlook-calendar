# outlook_parser.py
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import time
from datetime import datetime, timedelta
from dateutil import parser, tz
import tempfile

from cache import JsonCache
from killchrome import kill_leftover_chrome

class OutlookParser:
    def __init__(self, command: str="today all"):
        self.command = command.lower().strip()
        self.options = Options()
        self.options.add_argument("--headless=new")
        self.options.add_argument("--disable-gpu")
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")  # use /tmp instead of /dev/shm
        self.options.add_argument("--disable-extensions")  # disable extensions
        self.options.add_argument("--blink-settings=imagesEnabled=false")
        self.options.add_argument("--remote-debugging-port=9222")
        self.options.add_argument("--window-size=1920,1080")

        # Create a temporary unique user-data directory for Chrome
        self.temp_user_data_dir = tempfile.mkdtemp()
        self.options.add_argument(f"--user-data-dir={self.temp_user_data_dir}")

        # Explicitly use Chromium instead of Chrome
        self.options.binary_location = "/usr/bin/chromium-browser"

        # Explicitly point to chromedriver path
        service = Service("/usr/bin/chromedriver")
        self.driver = webdriver.Chrome(service=service, options=self.options)
        self.driver.set_page_load_timeout(240)

        self.local_tz = tz.tzlocal()
        self.target_date = self._resolve_target_date()
        self.items = []
        self.events = []

        # CACHE
        self.cache = JsonCache(expiry_minutes=60)

    def set_command(self, command: str):
        self.command = command.lower().strip()


    def _resolve_target_date(self):
        """Decide which date to get events for based on command."""
        today = datetime.now(self.local_tz).date()
        cmd = self.command.lower().strip()

        # Remove 'all' if present
        cmd = cmd.replace(" all", "")

        if "today" in cmd:
            return today
        elif "tomorrow" in cmd:
            return today + timedelta(days=1)
        elif cmd.isdigit():
            # A specific date number in current month
            return today.replace(day=int(cmd))
        else:
            return today  # default

    def fetch_events(self):
        print("Fetching events")
        """Load the Outlook published calendar and intercept the JSON events."""
        url = (
            "https://outlook.office365.com/calendar/published/"
            "ff41626f2a4e4ee0a459000db28a7535@acphs.edu/"
            "f814c4c342ad44a6975f38f9293124e414329295217178850134/calendar.html"
        )
        try:
            self.driver.get(url)
        except Exception as e:
            print(f"❌ Error loading calendar page: {e}")
            self.driver.quit()
            return []

        print("Done getting URL")
        print("Capturing events")
        # Hook fetch() to capture calendar data
        self.driver.execute_script("""
        window.collectedEvents = [];
        const origFetch = window.fetch;
        window.fetch = function() {
            return origFetch.apply(this, arguments).then(response => {
                try {
                    response.clone().json().then(data => {
                        if (arguments[0].includes('FindItem')) {
                            window.collectedEvents.push(data);
                        }
                    }).catch(()=>{});
                } catch(e){}
                return response;
            });
        };
        """)
        counter = 0
        while counter < 10:
            try:
                events_json = self.driver.execute_script("return window.collectedEvents;")
                break
            except Exception as e:
                counter += 1
                print(f"script failed trying again. Try: {counter}-- Exception: {e}")
                time.sleep(3)
                continue

        print(f"Collected events: {len(events_json)}")
        self.driver.quit()
        print("Quit Driver")

        if not events_json:
            raise Exception("No data collected from Outlook calendar.")

        try:
            self.items = events_json[0]["Body"]["ResponseMessages"]["Items"][0]["RootFolder"]["Items"]
        except Exception as e:
            raise Exception(f"Error parsing JSON structure: {e}")

    def parse_events(self):
        """Filter events for the selected date."""
        if not self.items:
            raise Exception("No items to parse — run fetch_events() first.")

        for item in self.items:
            start_str = item.get("Start")
            end_str = item.get("End")
            subject = item.get("Subject", "No Title")
            raw_location = item.get("Location", {}).get("DisplayName", "No Location")
            # Remove anything in parentheses (like addresses)
            location = raw_location.split(" (")[0].strip()
            location = location.split(", ")[0].strip()

            if not start_str:
                continue

            start_dt = parser.isoparse(start_str).astimezone(self.local_tz)
            end_dt = parser.isoparse(end_str).astimezone(self.local_tz) if end_str else None

            if start_dt.date() == self.target_date:
                start_fmt = start_dt.strftime("%I:%M %p")
                end_fmt = end_dt.strftime("%I:%M %p") if end_dt else "?"
                self.events.append(f"🕒 {start_fmt} - {end_fmt} | {subject} @ {location}")

    def get_results(self):
        """Return formatted text list for Discord or terminal."""
        kill_leftover_chrome()

        header = f"📅 Events for {self.target_date.strftime('%A, %B %d, %Y')}"
        if not self.events:
            return [header, "No events found."]

        show_all = self.command.endswith("all")  # e.g., "$cal today all"
        print(f"show_all {show_all}")

        track_locations = "ACPHS Track & Field Facility"

        formatted_events = []
        for e in self.events:
            if "Track & Field" in e:  # or however you define track_locations
                e = "**🏟️ " + e + "**"  # highlight
            formatted_events.append(e)

        if not show_all:
            # Only show track events
            track_only = [ev for ev in formatted_events if "🏟️" in ev]
            return [header] + track_only

        # Show all events, with track ones highlighted
        return [header] + formatted_events

    def run(self):
        """Fetch, parse, and return cached events if available."""
        # Use a single cache key for all events (full JSON)
        cache_key = "all_events"
        cached_data = self.cache.load(cache_key)

        if cached_data:
            print("Found cached data")
            # Filter cached events for the target date
            self.items = cached_data
            self.parse_events()
            return self.get_results()

        print("No cached data")
        # If cache is empty or expired, fetch from Outlook
        self.fetch_events()

        # Save raw fetched items to cache
        self.cache.save(cache_key, self.items)

        # Then parse for the specific day
        self.parse_events()
        return self.get_results()
