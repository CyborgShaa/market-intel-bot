import os
import json
import time
from datetime import datetime, timedelta, timezone
import requests
from decouple import config

# Import our custom modules
import telegram_bot
import gemini_analyzer

# --- Configuration ---
IMPACT_FILTER = ['low', 'medium', 'high']
COUNTRY_FILTER = ['US', 'EZ', 'CN', 'GB', 'JP', 'DE', 'FR', 'AU', 'CH', 'IN']
PRE_ALERT_MINUTES = 5
STATE_FILE = 'processed_events.json'
SCHEDULE_FILE = 'todays_schedule.json'

# --- Securely load API keys from environment variables ---
# *** IMPORTANT: Use your FMP API Key for this variable ***
FMP_API_KEY = config('FMP_API_KEY', default=None)


# --- State and Schedule Management ---
def load_json_file(filename, default_value):
    if not os.path.exists(filename):
        return default_value
    with open(filename, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return default_value

def save_json_file(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

def save_processed_event(event_id):
    processed_events = set(load_json_file(STATE_FILE, []))
    processed_events.add(event_id)
    save_json_file(STATE_FILE, list(processed_events))

# --- Core Functions ---
def fetch_daily_schedule():
    """Makes one API call to get the schedule for the next 24 hours."""
    if not FMP_API_KEY:
        print("FATAL ERROR: FMP_API_KEY not set.")
        return None
    
    print("INFO: Fetching new daily schedule from FMP...")
    try:
        # FMP's endpoint requires no date for the current day's calendar
        url = f"https://financialmodelingprep.com/api/v3/economic_calendar?apikey={FMP_API_KEY}"
        response = requests.get(url)
        response.raise_for_status()
        schedule = response.json()
        save_json_file(SCHEDULE_FILE, schedule)
        print(f"SUCCESS: Saved schedule with {len(schedule)} events.")
        return schedule
    except Exception as e:
        print(f"ERROR: Could not fetch daily schedule. Error: {e}")
        return None

def run_bot():
    """The main long-running service loop for the bot."""
    last_schedule_fetch_date = None
    
    while True:
        try:
            now_utc = datetime.now(timezone.utc)
            
            # --- 1. Daily Schedule Fetch Logic ---
            if last_schedule_fetch_date != now_utc.date():
                schedule = fetch_daily_schedule()
                if schedule is not None:
                    last_schedule_fetch_date = now_utc.date()
                else:
                    time.sleep(60) # Wait a minute before retrying if fetch fails
                    continue
            
            # --- 2. Check if we are near any event ---
            schedule = load_json_file(SCHEDULE_FILE, [])
            is_active_window = False
            for event in schedule:
                # FMP uses ISO format with 'Z' for UTC
                event_time_utc = datetime.fromisoformat(event['date'].replace('Z', '+00:00'))
                time_to_event = event_time_utc - now_utc
                time_since_event = now_utc - event_time_utc
                
                # Active window is from 5 mins before to 3 mins after event
                if timedelta(minutes=-PRE_ALERT_MINUTES) <= time_to_event <= timedelta(minutes=3):
                    is_active_window = True
                    break # Found an event in the window, no need to check others
            
            # --- 3. The "Burst Mode" API Call ---
            live_data = []
            if is_active_window:
                print("INFO: Active window detected. Fetching live data...")
                # We re-fetch the calendar to get the 'actual' values
                live_data = fetch_daily_schedule() # This will be our "live" data check
            else:
                print(f"INFO: Dormant state. No events nearby. Sleeping... ({now_utc.strftime('%H:%M:%S')})")

            # --- 4. Process Events ---
            processed_ids = set(load_json_file(STATE_FILE, []))
            # Use live_data if available, otherwise the saved schedule for pre-alerts
            events_to_process = live_data if live_data is not None else schedule

            for event in events_to_process:
                if event.get('impact') not in IMPACT_FILTER or event.get('country') not in COUNTRY_FILTER:
                    continue

                event_time_utc = datetime.fromisoformat(event['date'].replace('Z', '+00:00'))
                event_id = f"{event['eventName']}-{event['country']}-{event['date']}"
                pre_alert_id = f"pre-{event_id}"
                post_analysis_id = f"post-{event_id}"

                # Pre-Alert Logic
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
                
                # Post-Analysis Logic
                if event.get('actual') is not None:
                    time_since_release = now_utc - event_time_utc
                    if timedelta(minutes=0) <= time_since_release < timedelta(minutes=3):
                        if post_analysis_id not in processed_ids:
                            print(f"ACTION: Performing post-event analysis for {event['eventName']}")
                            # We need to adapt the keys for Gemini to match FMP's output
                            fmp_event_data = {
                                'country': event.get('country'),
                                'eventName': event.get('eventName'),
                                'actual': event.get('actual'),
                                'forecast': event.get('estimate'), # FMP uses 'estimate'
                                'prev': event.get('previous') # FMP uses 'previous'
                            }
                            analysis = gemini_analyzer.analyze_event(fmp_event_data)
                            
                            if analysis and "error" not in analysis:
                                message = (f"📈 *New Economic Data: {event['eventName']} ({event['country']})*\n\n"
                                           f"*Summary:* {analysis.get('summary')}\n\n"
                                           f"*Analysis:* {analysis.get('analysis')}\n\n"
                                           f"*Impact on Commodities:* {analysis.get('impact_on_commodities')}\n\n"
                                           f"*Gold Impact Score:* {analysis.get('gold_impact_score')}/10\n"
                                           f"*Silver Impact Score:* {analysis.get('silver_impact_score')}/10")
                                telegram_bot.send_message(message)
                                save_processed_event(post_analysis_id)
            
            time.sleep(60) # Wait for 60 seconds before the next check

        except Exception as e:
            print(f"FATAL ERROR in main loop: {e}")
            telegram_bot.send_message(f"🚨 **Bot Error!** 🚨\n\nA fatal error occurred: {e}")
            time.sleep(300) # Wait 5 minutes before restarting after a major crash

if __name__ == "__main__":
    run_bot()

