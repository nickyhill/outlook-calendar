# outlook_parser.py
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
from datetime import datetime, timedelta
from dateutil import parser, tz
import tempfile

from cache import JsonCache

class OutlookParser:
    def __init__(self, command: str):
        self.command = command.lower().strip()
        self.options = Options()
        self.options.add_argument("--headless=new")
        self.options.add_argument("--disable-gpu")
        self.options.add_argument("--no-sandbox")

        # Create a temporary unique user-data directory for Chrome
        self.temp_user_data_dir = tempfile.mkdtemp()
        self.options.add_argument(f"--user-data-dir={self.temp_user_data_dir}")
        self.driver = webdriver.Chrome(options=self.options)

        self.local_tz = tz.tzlocal()
        self.target_date = self._resolve_target_date()
        self.items = []
        self.events = []

        # CACHE
        self.cache = JsonCache()

    def _resolve_target_date(self):
        """Decide which date to get events for based on command."""
        today = datetime.now(self.local_tz).date()

        if self.command == "today":
            return today
        elif self.command == "tomorrow":
            return today + timedelta(days=1)
        elif self.command.isdigit():
            # A specific date number in current month
            return today.replace(day=int(self.command))
        else:
            return today  # default

    def fetch_events(self):
        """Load the Outlook published calendar and intercept the JSON events."""
        url = (
            "https://outlook.office365.com/calendar/published/"
            "ff41626f2a4e4ee0a459000db28a7535@acphs.edu/"
            "f814c4c342ad44a6975f38f9293124e414329295217178850134/calendar.html"
        )
        self.driver.get(url)

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

        time.sleep(5)
        events_json = self.driver.execute_script("return window.collectedEvents;")
        self.driver.quit()

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
        header = f"📅 Events for {self.target_date.strftime('%A, %B %d, %Y')}"
        if not self.events:
            return [header, "No events found."]
        return [header] + self.events

    def run(self):
        """Full pipeline in one call."""

        """Fetch, parse, and return cached events if available."""
        cache_key = f"{self.command}_{self.target_date}"
        cached_events = self.cache.load(cache_key)
        if cached_events:
            return cached_events

        self.fetch_events()
        self.parse_events()
        results = self.get_results()
        self.cache.save(cache_key, results)
        return results
