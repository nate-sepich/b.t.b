import os
import json
from decimal import Decimal
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
import google.generativeai as genai
import re
import uuid

# Load environment variables
load_dotenv()

# Check if GOOGLE_API_KEY is set
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY environment variable not set")

# Configure the Google Generative AI client
genai.configure(api_key=api_key)

# Preprocessing function to clean OCR text
def preprocess_text(text: str) -> str:
    # Replace 'S' followed by a number with '$'
    text = re.sub(r'S(?=\d)', '$', text)

    # Correct 'Ist' to '1st'
    text = text.replace('Ist', '1st')

    # Replace underscores with commas
    text = text.replace('_', ',')

    # Additional corrections as needed
    return text

# Improved function to generate content from LLM
def generate_content_from_model(extracted_text: str) -> dict:
    # Define the schema based on the Pydantic model
    output_json_template = {
        "user_id": "Nate",
        "bet_id": str(uuid.uuid4()),
        "upload_timestamp": str(datetime.utcnow()),
        "league": None,
        "season": None,
        "date": None,
        "game_id": None,
        "away_team": None,
        "home_team": None,
        "wager_team": None,
        "bet_type": None,
        "selection": None,
        "odds": None,
        "risk": None,
        "to_win": None,
        "payout": None,
        "outcome": None,
        "profit_loss": None
    }

    try:
        # Preprocess the extracted text to correct common OCR errors
        cleaned_text = preprocess_text(extracted_text)

        # Initialize the model
        model = genai.GenerativeModel('gemini-1.5-flash')

        # Enhanced Prompt Structure
        prompt = f"""
        You are a highly capable model tasked with parsing betting slip information. The text may contain OCR errors.
        Please extract the relevant information from the following text and populate a JSON object based on the schema provided.

        Important Instructions:
        - Dollar signs ($) might be misread as 'S'. Make corrections where applicable.
        - Match the fields to the correct types. For example:
          - "outcome" must be one of ['WON', 'LOST', 'PUSH', 'PENDING'].
          - "bet_type" must be one of ['Moneyline', 'Spread', 'Totals', 'Prop', 'Future', 'Other'].
        - Multiple monetary values may be present. Distinguish between "risk", "payout", and "to_win".
        - Use the context of words like 'BET', 'PAYOUT', 'Settled' to determine appropriate values.
        - Dates are in the format 'MMM DD, YYYY at HH:MM AM/PM' in most cases.

        **Text:**
        "{cleaned_text}"

        **Schema Template:**
        {json.dumps(output_json_template, indent=2)}

        Ensure the JSON object is valid and accurately fills in all the fields based on the given text. If any field cannot be determined, leave it as null.

        Example:
        Given a similar text input, here is how the JSON should be structured:
        {{
          "user_id": "Nate",
          "bet_id": "ABCDEFGHIJKL",
          "upload_timestamp": "2024-09-15T13:00:00",
          "league": "NFL",
          "season": 2024,
          "date": "2024-09-22T15:25:00",
          "game_id": "GAME12345",
          "away_team": "BAL Ravens",
          "home_team": "DAL Cowboys",
          "wager_team": "BAL Ravens",
          "bet_type": "Totals",
          "selection": "Over 23.5",
          "odds": "-120",
          "risk": "61.21",
          "to_win": "51.01",
          "payout": "112.22",
          "outcome": "WON",
          "profit_loss": "51.01"
        }}

        Please output the resulting JSON object without additional commentary.
        """

        # Generate content from LLM
        response = model.generate_content(prompt)

        # Extract the content from the response object (adjust this based on actual response structure)
        if hasattr(response, 'text'):
            content = response.text
        else:
            content = str(response)

        # Clean up the response content by removing markdown formatting
        cleaned_content = content.replace("```json", "").replace("```", "").strip()

    except Exception as e:
        raise RuntimeError(f"Failed to get a response from LLM: {str(e)}")

    # Handling response and JSON parsing
    try:
        # Attempt to parse the cleaned response content as JSON
        parsed_data = json.loads(cleaned_content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse the response as JSON: {str(e)}")

    # Validate parsed data to ensure critical fields are populated correctly
    parsed_data = validate_and_correct_output(parsed_data, cleaned_text)

    return parsed_data

# Function to validate and correct the LLM output
def validate_and_correct_output(parsed_data: dict, original_text: str) -> dict:
    # List of fields that must not be null
    critical_fields = ["bet_id", "bet_type", "risk", "odds", "away_team", "home_team", "date"]

    # Iterate over the critical fields and check if they are filled
    for field in critical_fields:
        if parsed_data.get(field) is None:
            # If the field is missing, try re-extracting using regex or add a placeholder for later correction
            parsed_data[field] = extract_fallback_field(field, original_text)

    # Convert specific fields to correct types
    if parsed_data.get("risk"):
        parsed_data["risk"] = str(parsed_data["risk"])
    if parsed_data.get("to_win"):
        parsed_data["to_win"] = str(parsed_data["to_win"])
    if parsed_data.get("payout"):
        parsed_data["payout"] = str(parsed_data["payout"])
    if parsed_data.get("profit_loss"):
        try:
            parsed_data["profit_loss"] = Decimal(parsed_data["profit_loss"])
        except:
            parsed_data["profit_loss"] = None  # Set to None if it can't be converted

    return parsed_data

# Fallback extraction function using regex
def extract_fallback_field(field_name: str, text: str) -> Optional[str]:
    if field_name in ["risk", "to_win", "payout"]:
        # Extract the first occurrence of a dollar amount as a fallback
        match = re.search(r'\$\d+(\.\d{2})?', text)
        if match:
            return match.group().replace('$', '')
    elif field_name in ["away_team", "home_team"]:
        # Attempt to extract team names based on common patterns
        teams = re.findall(r'\b[A-Z]{3,}\s[A-Za-z]+\b', text)
        if teams:
            if field_name == "away_team":
                return teams[0]
            elif len(teams) > 1:
                return teams[1]
    # Additional fallback logic for other fields as needed
    return None

# Example Usage
if __name__ == "__main__":
    extracted_text = """
    Straight Win S112.22 Over 23.5 -120 Ist Half Total Points Final Gamecast 
    BAL Ravens DAL Cowboys Sep 22_ 2024 at 3.25 PM S61.21 S112.22 BET PAYOUT 
    Share Settled: Sep 22, 2024 at 4.50 PM ID: ZuD9zrKPttNNBkLtpsoAl3xl8Ac =
    """

    parsed_output = generate_content_from_model(extracted_text)
    print(parsed_output)
