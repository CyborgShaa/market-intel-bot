import os
import requests
import json
from datetime import date

def fetch_economic_calendar():
    """
    Fetches economic calendar data and prints it.
    Reads the Finnhub API key from an environment variable.
    """
    # --- Securely get API key from environment variables ---
    api_key = os.environ.get('FINNHUB_API_KEY')

    if not api_key:
        print("FATAL ERROR: FINNHUB_API_KEY environment variable not set.")
        return # Exit the function if key is missing

    today_str = date.today().strftime("%Y-%m-%d")
    print(f"INFO: Running job to fetch economic data for {today_str}")

    try:
        url = f"https://finnhub.io/api/v1/calendar/economic?token={api_key}&from={today_str}&to={today_str}"
        response = requests.get(url)
        response.raise_for_status() # Check for request errors

        data = response.json().get('economicCalendar', [])
        
        if data:
            print("SUCCESS: Found {} events for today.".format(len(data)))
            # For logging purposes, let's just print the event names
            for event in data:
                print(f"  - Event: {event.get('eventName')}, Time: {event.get('time')}, Country: {event.get('country')}")
        else:
            print("INFO: No economic events found for today.")

    except requests.exceptions.RequestException as e:
        print(f"ERROR: API request failed. Error: {e}")
    except Exception as e:
        print(f"ERROR: An unexpected error occurred. Error: {e}")

if __name__ == "__main__":
    fetch_economic_calendar()

