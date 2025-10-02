import google.generativeai as genai
from decouple import config
import json

# --- Configuration ---
GEMINI_API_KEY = config('GEMINI_API_KEY', default=None)

# Configure the Gemini client
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def analyze_event(event_data):
    """
    Sends economic event data to Gemini for analysis and returns a structured response.
    'event_data' should be a dictionary for a single event from Finnhub.
    """
    if not GEMINI_API_KEY:
        return {"error": "Gemini API key not configured."}

    model = genai.GenerativeModel('gemini-pro')

    prompt = f"""
    You are an expert financial analyst specializing in the commodities market, with a deep understanding of how economic indicators affect Gold (XAU/USD) and Silver (XAG/USD).

    Analyze the following just-released economic data point and return your response ONLY in a JSON format. Do not add any other text, explanation, or markdown formatting outside of the JSON structure.

    Input Data:
    {{
      "country": "{event_data.get('country')}",
      "eventName": "{event_data.get('eventName')}",
      "actual": {event_data.get('actual')},
      "forecast": {event_data.get('forecast')},
      "previous": {event_data.get('prev')}
    }}

    Required JSON Output Structure:
    {{
      "summary": "A brief, 1-2 sentence explanation of what this economic indicator is, in Hinglish.",
      "analysis": "A short analysis comparing the 'actual' to the 'forecast' values and what this means, in Hinglish.",
      "impact_on_commodities": "An explanation of the likely short-term impact on Gold and Silver, explaining the reasoning (effect on USD, Fed policy, etc.), in Hinglish.",
      "gold_impact_score": <An integer from 1 to 10>,
      "silver_impact_score": <An integer from 1 to 10>
    }}
    """

    try:
        response = model.generate_content(prompt)
        # Clean up the response to ensure it's valid JSON
        cleaned_json = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(cleaned_json)
    except Exception as e:
        print(f"ERROR: Failed to get analysis from Gemini. Error: {e}")
        return {"error": str(e)}

      
