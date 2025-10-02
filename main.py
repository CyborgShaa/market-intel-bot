import os
import json
from datetime import datetime, timedelta, timezone

import requests
from decouple import config

# Import our custom modules
import telegram_bot
import gemini_analyzer

# --- Configuration ---
# These settings control the bot's behavior.
# You can add more countries or impacts as needed.
IMPACT_FILTER = ['low', 'medium', 'high']  # Options: 'low', 'medium', 'high'
COUNTRY_FILTER = ['US', 'EZ', 'CN', 'GB', 'JP', 'DE', 'FR', 'AU', 'CA', 'CH', 'IN']  # ISO 2-letter country codes
PRE_ALERT_MINUTES = 5  # How many minutes before an event to send a pre-alert
STATE_FILE = 'processed_events.json' # File to log processed events to prevent duplicates

# --- Securely load API keys from environment variables ---
FINNHUB_API_KEY = config('FINNHUB_API_KEY', default=None)

# --- State Management Functions ---
def load_processed_events():
    """Loads the set of processed event IDs from the state file."""
    if not os.path.exists(STATE_FILE):
        return set()
    with open(STATE_FILE, 'r') as f:
        try:
            return set(json.load(f))
        except json.JSONDecodeError:
            return set()

def save_processed_event(event_id):
    """Saves a new processed event ID to the state file."""
    processed_events = load_processed_events()
    processed_events.add(event_id)
    with open(STATE_FILE, 'w') as f:
        json.dump(list(processed_events), f)

# --- Main Logic ---
def run_checker():
    """The main function executed by the scheduler."""
    if not FINNHUB_API_KEY:
        print("FATAL ERROR: FINNHUB_API_KEY not set.")
        return

    processed_ids = load_processed_events()
    now_utc = datetime.now(timezone.utc)
    today_str = now_utc.strftime("%Y-%m-%d")
    
    print(f"\nINFO: Running job at {now_utc.isoformat()}")

    try:
        url = f"https://finnhub.io/api/v1/calendar/economic?token={FINNHUB_API_KEY}&from={today_str}&to={today_str}"
        response = requests.get(url)
        response.raise_for_status()
        events = response.json().get('economicCalendar', [])
        
        if not events:
            print("INFO: No economic events found for today.")
            return

        print(f"INFO: Found {len(events)} total events for today. Filtering...")

        for event in events:
            # --- Filtering ---
            if event.get('impact') not in IMPACT_FILTER or event.get('country') not in COUNTRY_FILTER:
                continue

            # --- Time Conversion ---
            # Finnhub time is in UTC. We make our datetime objects timezone-aware to prevent errors.
            event_time_utc = datetime.strptime(event['time'], '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
            
            # Create unique IDs for pre-alerts and post-analysis to track them separately
            event_id = f"{event['eventName']}-{event['country']}-{event['time']}"
            pre_alert_id = f"pre-{event_id}"
            post_analysis_id = f"post-{event_id}"

            # --- 1. Pre-Event Alert Logic ---
            time_to_event = event_time_utc - now_utc
            if timedelta(minutes=0) < time_to_event <= timedelta(minutes=PRE_ALERT_MINUTES):
                if pre_alert_id not in processed_ids:
                    print(f"ACTION: Sending pre-event alert for {event['eventName']}")
                    minutes_left = int(time_to_event.total_seconds() / 60)
                    message = (f"⚠️ *Heads-Up Alert!* ⚠️\n\n"
                               f"**Event:** {event['eventName']} ({event['country']})\n"
                               f"**Releasing in:** Approximately {minutes_left} minutes")
                    telegram_bot.send_message(message)
                    save_processed_event(pre_alert_id)

            # --- 2. Post-Event Analysis Logic ---
            if event.get('actual') is not None: # Check if data has been released
                time_since_release = now_utc - event_time_utc
                # Check if it was released within the last 2 minutes to be safe
                if timedelta(minutes=0) <= time_since_release < timedelta(minutes=2):
                    if post_analysis_id not in processed_ids:
                        print(f"ACTION: Performing post-event analysis for {event['eventName']}")
                        analysis = gemini_analyzer.analyze_event(event)
                        
                        if analysis and "error" not in analysis:
                            message = (f"📈 *New Economic Data: {event['eventName']} ({event['country']})*\n\n"
                                       f"*Summary:* {analysis.get('summary')}\n\n"
                                       f"*Analysis:* {analysis.get('analysis')}\n\n"
                                       f"*Impact on Commodities:* {analysis.get('impact_on_commodities')}\n\n"
                                       f"*Gold Impact Score:* {analysis.get('gold_impact_score')}/10\n"
                                       f"*Silver Impact Score:* {analysis.get('silver_impact_score')}/10")
                            telegram_bot.send_message(message)
                            save_processed_event(post_analysis_id)
                        else:
                            print(f"ERROR: Gemini analysis failed. Response: {analysis.get('error')}")

    except Exception as e:
        print(f"FATAL ERROR in main loop: {e}")
        telegram_bot.send_message(f"🚨 **Bot Error!** 🚨\n\nA fatal error occurred in the main script: {e}")

if __name__ == "__main__":
    run_checker()

