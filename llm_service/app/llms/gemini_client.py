import os
import json
from decimal import Decimal
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
import google.generativeai as genai
import re
import uuid
import time


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

# Improved function to generate content from LLM for multiple bets
def generate_content_from_model(extracted_text: str) -> list:
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
        model = genai.GenerativeModel('gemini-1.5-pro-002')

        # Enhanced Prompt Structure
        prompt = f"""
        You are a highly capable model tasked with parsing betting slip information. The text may contain OCR errors.
        Please extract the relevant information for each bet from the following text and populate a list of JSON objects based on the schema provided.

        Important Instructions:
        - Dollar signs ($) might be misread as 'S'. Make corrections where applicable.
        - Match the fields to the correct types. For example:
          - "outcome" must be one of ['WON', 'LOST', 'PUSH', 'PENDING'].
          - "bet_type" must be one of ['Moneyline', 'Spread', 'Totals', 'Prop', 'Future', 'Other'].
        - Multiple monetary values may be present. Distinguish between "risk", "payout", and "to_win".
        - Use the context of words like 'BET', 'PAYOUT', 'Settled' to determine appropriate values.
        - Dates are in the format 'MMM DD, YYYY at HH:MM AM/PM' in most cases.
        - Extract all bets if there are multiple in the text.

        **Text:**
        "{cleaned_text}"

        **Schema Template:**
        {json.dumps(output_json_template, indent=2)}

        Ensure each JSON object is valid and accurately fills in all the fields based on the given text. If any field cannot be determined, leave it as null.

        Example:
        Given a similar text input, here is how the JSON should be structured:
        [
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
        ]

        Please output the resulting list of JSON objects without additional commentary.
        """
        # print(prompt)

        # Generate content from LLM
        response = model.generate_content(prompt)

        # Extract the content from the response object (adjust this based on actual response structure)
        if hasattr(response, 'text'):
            content = response.text
        else:
            content = str(response)
        # print(content)
        # Clean up the response content by removing markdown formatting
        cleaned_content = content.replace("```json", "").replace("```", "").strip()

    except Exception as e:
        raise RuntimeError(f"Failed to get a response from LLM: {str(e)}")

    # Handling response and JSON parsing
    try:
        # Attempt to parse the cleaned response content as a list of JSON objects
        parsed_data = json.loads(cleaned_content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse the response as JSON: {str(e)}")

    # Validate parsed data to ensure critical fields are populated correctly for each bet
    validated_data = [validate_and_correct_output(bet, cleaned_text) for bet in parsed_data]

    return validated_data

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

# Function to split context into manageable batches while avoiding splits within betslips
def split_context_for_batches(text: str, model_name: str = 'gemini-1.5-flash', max_chunk_size: int = 1000) -> list:
    """
    Uses the Gemini Pro model to split input text into manageable, logical batches while avoiding splits within individual betslips.

    Parameters:
    - text (str): The entire input text to be split.
    - model_name (str): The Gemini model to be used for splitting.
    - max_chunk_size (int): The maximum number of characters per chunk.

    Returns:
    - List of text segments, each containing logically grouped bet information.
    """
    # Helper function to split text into chunks but avoid breaking betslips
    def chunk_text_safely(text, chunk_size):
        betslip_pattern = re.compile(r"(Betslip ID: \w+)", re.IGNORECASE)
        chunks = []
        current_chunk = ""
        for line in text.splitlines():
            # If the line starts a new betslip and the current chunk is already large enough
            if betslip_pattern.match(line) and len(current_chunk) + len(line) > chunk_size:
                chunks.append(current_chunk)
                current_chunk = line  # Start a new chunk
            else:
                current_chunk += "\n" + line

        # Add any remaining text to chunks
        if current_chunk:
            chunks.append(current_chunk)
        return chunks

    # Initialize the model
    model = genai.GenerativeModel(model_name)

    batches = []
    
    # Safely chunk the text
    chunks = chunk_text_safely(text, max_chunk_size)
    
    for chunk in chunks:
        # Use a minimal, token-efficient prompt
        prompt = f"""
        Split the following text into logical sections based on individual betslips. Do not add or modify any content. Each section must contain the full details of a single betslip without splitting information across batches.

        Text:
        {chunk}
        """
        result = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=list[str]
            )
        )
        try:
            batch = json.loads(result.text)
            batches.extend(batch)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON response: {e}")
            continue
    
    return batches

# Function to process each batch using a smaller model (e.g., Gemini Flash)
def parse_bet_data_with_flash_model(batch: str, model_name: str = 'gemini-1.5-flash') -> dict:
    """
    Sends a batch to the Gemini Flash model for processing.

    Parameters:
    - batch (str): The text batch to be processed.
    - model_name (str): The Gemini model to be used for parsing.

    Returns:
    - Parsed response from the Flash model.
    """
    # Initialize the model
    model = genai.GenerativeModel(model_name)

    # Prepare the prompt for parsing the batch
    prompt = f"""
    You will now process the following batch of bet information:

    **Batch Segment:**
    "{batch}"

    Extract bet details in JSON format using the following schema:
    {{
      "user_id": "Nate",
      "bet_id": "<unique-identifier>",
      "upload_timestamp": "<timestamp>",
      "league": "<league-name>",
      "season": "<season-year>",
      "date": "<bet-date>",
      "game_id": "<game-id>",
      "away_team": "<team-name>",
      "home_team": "<team-name>",
      "wager_team": "<team-name>",
      "bet_type": "<bet-type>",
      "selection": "<bet-selection>",
      "odds": "<odds>",
      "risk": "<risk-amount>",
      "to_win": "<to-win-amount>",
      "payout": "<payout-amount>",
      "outcome": "<outcome-status>",
      "profit_loss": "<profit-or-loss>"
    }}
    """

    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json"
        )
    )
    try:
        return json.loads(response.text)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response: {e}")
        return {}

import concurrent.futures
def parse_mgm_pdf_inputs(extracted_text: str): # Extracted text from the PDF
    # Step 1: Use the Pro model to create batches
    text_segments = split_context_for_batches(extracted_text)
    # print(text_segments)
    all_data = []

    for i, segment in enumerate(text_segments):
        parsed_data = parse_bet_data_with_flash_model(segment)
        print(parsed_data)
        cleaned_data = validate_and_correct_output(parsed_data, segment)
        try:
            print("Parsed Bet Data:", cleaned_data)  # Here you can save the parsed data to your database or take further action
            all_data.append(parsed_data)
        except Exception as e:
            print(f"Error processing segment {segment}: {e}")
    return all_data

# Example Usage
if __name__ == "__main__":
    extracted_text = """
My Bets
9/28/24
9/27/24Betslip ID: 1ZRN21G87M
Result:Under 46.5
Buffalo Bills at Baltimore Ravens
9/29/24 • 7:20 PM
Bet placement Stake Odds Payout (inc Stake)
9/29/24 • 6:33 PM $60.00 -110 -LOST
Over 46.5Totals
Betslip ID: 1ZRMM8MSW4
Result:Over 21
New Orleans Saints at Atlanta Falcons
9/29/24 • 12:02 PM
Bet placement Stake Odds Payout (inc Stake)
9/29/24 • 11:44 AM $50.00 -130 -LOST
Under 211st Half Totals
Betslip ID: 1ZRMM3ZHD0
Result:Over 20.5
New Orleans Saints at Atlanta Falcons
9/29/24 • 12:02 PM
Bet placement Stake Odds Payout (inc Stake)
9/29/24 • 11:39 AM $20.00 -115 -LOST
Under 20.51st Half Totals
Betslip ID: 1ZRLD9X9RS
Result:Under 50.5
Arkansas at Texas A&M (Neutral Venue)
9/28/24 • 2:30 PM
Bet placement Stake Odds Payout (inc Stake)
9/28/24 • 2:25 PM $15.00 -105 $29.29WON
Under 50.5Totals10/4/24, 10:52 PM BetMGM
https://sports.ia.betmgm.com/en/sports/my-bets/settled 1/11Betslip ID: 1ZRLD9WCD4
Result:Oklahoma
Oklahoma at Auburn
9/28/24 • 2:30 PM
Bet placement Stake Odds Payout (inc Stake)
9/28/24 • 2:25 PM $15.00 -115 -LOST
AuburnMoney Line
Betslip ID: 1ZRL702EGZ
Result:Arkansas +5.5
Arkansas at Texas A&M (Neutral Venue)
9/28/24 • 2:30 PM
Bet placement Stake Odds Payout (inc Stake)
9/28/24 • 11:04 AM $15.00 -105 $29.29WON
Arkansas +5.5Spread
Betslip ID: 1ZRL700RMB
Result:Clemson -22.5
Stanford at Clemson
9/28/24 • 6:00 PM
Bet placement Stake Odds Payout (inc Stake)
9/28/24 • 11:04 AM $15.00 -110 $28.64WON
Clemson -22.5Spread
Betslip ID: 1ZRL6ZYTEW
Result:Over 49.5
Georgia at Alabama
9/28/24 • 6:30 PM
Bet placement Stake Odds Payout (inc Stake)
9/28/24 • 11:03 AM $15.00 -110 -LOST
Under 49.5Totals
Betslip ID: 1ZRL6ZXHLW
Cancellation Reason:Winning selection not available in the market. Any Bonus Bets used will be refunded
within 24 hours.
Cincinnati U at Texas Tech
9/28/24 • 7:00 PM
Bet placement Stake Odds Payout (inc Stake)
9/28/24 • 11:03 AM $15.00 -105 $15.00CANCELLED
Cincinnati U +3Spread10/4/24, 10:52 PM BetMGM
https://sports.ia.betmgm.com/en/sports/my-bets/settled 2/119/25/24Betslip ID: 1ZRL6YTAUR
Result:Kansas State -6
Oklahoma State at Kansas State
9/28/24 • 11:03 AM
Bet placement Stake Odds Payout (inc Stake)
9/28/24 • 11:02 AM $15.00 -110 $28.64WON
Kansas State -6Spread
Betslip ID: 1ZRL6XNC9W
Result:Under 55.5
North Carolina at Duke
9/28/24 • 3:00 PM
Bet placement Stake Odds Payout (inc Stake)
9/28/24 • 11:01 AM $15.00 -115 -LOST
Over 55.5Totals
Betslip ID: 1ZRL6T9XBK
Result:Northern Illinois +7.5
Northern Illinois at NC State
9/28/24 • 11:00 AM
Bet placement Stake Odds Payout (inc Stake)
9/28/24 • 10:58 AM $15.00 -120 $27.50WON
Northern Illinois +7.5Spread
Betslip ID: 1ZRHGEWA2Y
Result:Over 21.5
Philadelphia Eagles at Tampa Bay Buccaneers
9/29/24 • 12:00 PM
Bet placement Stake Odds Payout (inc Stake)
9/26/24 • 12:54 PM $60.00 -130 -LOST
Under 21.51st Half Totals10/4/24, 10:52 PM BetMGM
https://sports.ia.betmgm.com/en/sports/my-bets/settled 3/119/24/24
9/22/24
9/21/24Betslip ID: 1ZRG4ZWGMT
Result:Over 50.5
Washington Commanders at Arizona Cardinals
9/29/24 • 3:05 PM
Bet placement Stake Odds Payout (inc Stake)
9/25/24 • 1:43 PM $50.00 -110 $95.45WON
Over 50.5Totals
$10.00 in a Bonus Bet if your bet loses
Betslip ID: 1ZRCAHR1BX
Result:Chiefs
Kansas City Chiefs at Atlanta Falcons
9/22/24 • 7:20 PM
Bet placement Stake Odds Payout (inc Stake)
9/22/24 • 8:25 PM $25.00 +100 $50.00WON
ChiefsMoney Line
Betslip ID: 1ZRC0L24RG
Result:Over 39.5
Carolina Panthers at Las Vegas Raiders
9/22/24 • 3:05 PM
Bet placement Stake Odds Payout (inc Stake)
9/22/24 • 3:08 PM $50.00 -110 $95.45WON
Over 39.5Totals10/4/24, 10:52 PM BetMGM
https://sports.ia.betmgm.com/en/sports/my-bets/settled 4/119/20/24Parlay 2 picksBetslip ID: 1ZRC05J74G WON
Bet placement Stake Total odds Payout (inc Stake)
9/22/24 • 2:53 PM $5.00 +196 $14.81
Result:Lions
Detroit Lions at Arizona Cardinals
9/22/24 • 3:25 PM-155 LionsMoney Line

Result:Ravens
Baltimore Ravens at Dallas Cowboys
9/22/24 • 3:25 PM-125 RavensMoney Line
Betslip ID: 1ZRBMPE8FK
Result:Over 39
Carolina Panthers at Las Vegas Raiders
9/22/24 • 3:05 PM
Bet placement Stake Odds Payout (inc Stake)
9/22/24 • 9:19 AM $7.97 -130 $14.10WON
Over 39Totals
Betslip ID: 1ZRBMNDCGG
Result:Over 37
Green Bay Packers at Tennessee Titans
9/22/24 • 12:00 PM
Bet placement Stake Boosted Odds Payout (inc Stake)
9/22/24 • 9:18 AM $5.00 -115-110 $9.57WON
Over 37Totals
$9.35 in cash + Boosted winnings in $0.22 Cash
Betslip ID: 1ZRAETSBC9
Result:Under 59.5
Southern Miss at Jacksonville State
9/21/24 • 2:00 PM
Bet placement Stake Odds Payout (inc Stake)
9/21/24 • 12:34 PM $15.00 -105 -LOST
Over 59.5Totals10/4/24, 10:52 PM BetMGM
https://sports.ia.betmgm.com/en/sports/my-bets/settled 5/119/19/24
Betslip ID: 1ZR948E37C
Result:Under 35.5
Los Angeles Chargers at Pittsburgh Steelers
9/22/24 • 12:00 PM
Bet placement Stake Odds Payout (inc Stake)
9/20/24 • 1:52 PM $37.50 -110 $71.59WON
Under 35.5Totals
Betslip ID: 1ZR92E457L
Result:Utah +1
Utah at Oklahoma State
9/21/24 • 3:00 PM
Bet placement Stake Odds Payout (inc Stake)
9/20/24 • 12:54 PM $25.00 -110 -LOST
Oklahoma State -1Spread
Betslip ID: 1ZR92E44X8
Result:Vanderbilt +20.5
Vanderbilt at Missouri
9/21/24 • 3:15 PM
Bet placement Stake Boosted Odds Payout (inc Stake)
9/20/24 • 12:54 PM $5.00 -115-110 $9.57WON
Vanderbilt +20.5Spread
$9.35 in cash + Boosted winnings in $0.22 Cash
Betslip ID: 1ZR92CZDW0
Result:Denver Broncos +6.5
Denver Broncos at Tampa Bay Buccaneers
9/22/24 • 12:00 PM
Bet placement Stake Odds Payout (inc Stake)
9/20/24 • 12:52 PM $50.00 -105 $97.62WON
Denver Broncos +6.5Spread10/4/24, 10:52 PM BetMGM
https://sports.ia.betmgm.com/en/sports/my-bets/settled 6/119/18/24
9/14/24Betslip ID: 1ZR7XEKGDK
Result:Kansas City Chiefs -3
Kansas City Chiefs at Atlanta Falcons
9/22/24 • 7:20 PM
Bet placement Stake Odds Payout (inc Stake)
9/19/24 • 5:10 PM $50.00 -110 $95.45WON
Kansas City Chiefs -3Spread
Betslip ID: 1ZR23CPHXB
Result:Minnesota Vikings +1.5
San Francisco 49ers at Minnesota Vikings
9/15/24 • 12:03 PM
Bet placement Stake Odds Payout (inc Stake)
9/15/24 • 1:56 PM $5.00 +150 -LOST
San Francisco 49ers -1.5Spread
Parlay 2 picksBetslip ID: 1ZR1ZG4J9Y LOST
Bet placement Stake Total odds Payout (inc Stake)
9/15/24 • 11:52 AM $45.42 -154 -
Result:Tampa Bay Buccaneers +1.5
Tampa Bay Buccaneers at Detroit Lions
9/15/24 • 12:02 PM-350 Detroit Lions -1.5Spread

Result:Denver Broncos +8.5
Pittsburgh Steelers at Denver Broncos
9/15/24 • 3:25 PM-350 Denver Broncos +8.5Spread
Betslip ID: 1ZR1ZDP8Y0
Result:Washington Commanders -1.5
New York Giants at Washington Commanders
9/15/24 • 12:02 PM
Bet placement Stake Odds Payout (inc Stake)
9/15/24 • 11:49 AM $25.00 -110 -LOST
New York Giants +1.5Spread10/4/24, 10:52 PM BetMGM
https://sports.ia.betmgm.com/en/sports/my-bets/settled 7/119/13/24Betslip ID: 1ZR18DD8W9
Result:Over 17.5
Seattle Seahawks at New England Patriots
9/15/24 • 12:00 PM
Bet placement Stake Odds Payout (inc Stake)
9/14/24 • 11:33 PM $20.00 -120 -LOST
Under 17.5New England Patriots: Total points
Parlay 4 picksBetslip ID: 1ZR13TBTTN LOST
Bet placement Stake Total odds Payout (inc Stake)
9/14/24 • 9:06 PM $10.00 +801 -
Result:R. Rodriguez
Ode Osbourne (USA) - Ronaldo Rodriguez (MEX)
9/14/24 • 9:15 PM-190 R. RodriguezFight Result

Result:D. Lopes
Diego Lopes (BRA) - Brian Ortega (USA)
9/14/24 • 10:15 PM-185 D. LopesFight Result

Result:V. Shevchenko
Valentina Shevchenko (KGZ) - Alexa Grasso (MEX)
9/14/24 • 10:45 PM+105 V. ShevchenkoFight Result

Result:M. Dvalishvili
Merab Dvalishvili (USA) - Sean O'Malley (USA)
9/14/24 • 11:15 PM-115 S. O'MalleyFight Result
Betslip ID: 1ZR0TN2MHL
Cancellation Reason:Winning selection not available in the market. Any Bonus Bets used will be refunded
within 24 hours.
Connecticut at Duke
9/14/24 • 5:00 PM
Bet placement Stake Odds Payout (inc Stake)
9/14/24 • 4:14 PM $15.00 -110 $15.00CANCELLED
Over 47Totals10/4/24, 10:52 PM BetMGM
https://sports.ia.betmgm.com/en/sports/my-bets/settled 8/119/12/24Betslip ID: 1ZR0JEBLSJ
Result:Georgia State +9
Vanderbilt at Georgia State
9/14/24 • 6:00 PM
Bet placement Stake Odds Payout (inc Stake)
9/14/24 • 11:50 AM $15.00 -110 $28.64WON
Georgia State +9Spread
Betslip ID: 1ZR0E7NHR R
Result:Over 71
North Texas at Texas Tech
9/14/24 • 11:00 AM
Bet placement Stake Odds Payout (inc Stake)
9/14/24 • 9:35 AM $15.00 -110 $28.64WON
Over 71Totals
Betslip ID: 1ZR0E5HTXL
Result:Over 55.5
Ball State at Miami Florida
9/14/24 • 2:30 PM
Bet placement Stake Boosted Odds Payout (inc Stake)
9/14/24 • 9:33 AM $20.00 -110+109 $41.82WON
Over 55.5Totals
$38.18 in cash + Boosted winnings in $3.64 Cash
Betslip ID: 1ZPZJKJG4R
Result:Under 14.5
Cincinnati Bengals at Kansas City Chiefs
9/15/24 • 3:25 PM
Bet placement Stake Odds Payout (inc Stake)
9/13/24 • 6:51 PM $50.00 -125 -LOST
Over 14.5Isiah Pacheco (KC): Longest rush
Betslip ID: 1ZPZJ82F3X
Result:Under 30.5
Arizona at Kansas State
9/13/24 • 7:00 PM
Bet placement Stake Odds Payout (inc Stake)
9/13/24 • 6:40 PM $25.00 -105 -LOST
Over 30.51st Half Totals10/4/24, 10:52 PM BetMGM
https://sports.ia.betmgm.com/en/sports/my-bets/settled 9/119/9/24
9/7/24Betslip ID: 1ZPZ77DPBM
Result:Over 23.5
New Orleans Saints at Dallas Cowboys
9/15/24 • 12:00 PM
Bet placement Stake Odds Payout (inc Stake)
9/13/24 • 12:47 PM $50.00 -110 $95.45WON
Over 23.51st Half Totals
Betslip ID: 1ZPZ77DP4B
Result:Over 17.5
Seattle Seahawks at New England Patriots
9/15/24 • 12:00 PM
Bet placement Stake Odds Payout (inc Stake)
9/13/24 • 12:47 PM $20.00 -140 -LOST
Under 17.5New England Patriots: Total points
Betslip ID: 1ZPT0WMS1Y
Result:Under 48
Atlanta Falcons at Philadelphia Eagles
9/16/24 • 7:15 PM
Bet placement Stake Odds Payout (inc Stake)
9/9/24 • 8:04 PM $50.00 -110 $95.45WON
Under 48Totals
Betslip ID: 1ZPRDZKP47
Result:Over 43.5
Washington Commanders at Tampa Bay Buccaneers
9/8/24 • 3:25 PM
Bet placement Stake Boosted Odds Payout (inc Stake)
9/8/24 • 4:55 PM $20.00 -115+104 $40.87WON
Over 43.5Totals
$37.39 in cash + Boosted winnings in $3.48 Cash10/4/24, 10:52 PM BetMGM
https://sports.ia.betmgm.com/en/sports/my-bets/settled 10/119/5/24
9/4/24Betslip ID: 1ZPPZMAGZL
Result:Under 12.5
Jacksonville Jaguars at Miami Dolphins
9/8/24 • 12:00 PM
Bet placement Stake Odds Payout (inc Stake)
9/8/24 • 9:17 AM $29.01 -165 -LOST
Over 12.5Miami Dolphins: 1st half points
Betslip ID: 1ZPLD5GCZA
Result:Bet Lost
Kansas City Chiefs - Baltimore Ravens
9/5/24 • 7:43 PM
Bet placement Stake Odds Payout (inc Stake)
9/5/24 • 8:13 PM $1.00 +325 -LOST
Offensive Touchdown4th Drive Outcome
Betslip ID: 1ZPKXD3K3C
Result:Chicago Bears -4
Tennessee Titans at Chicago Bears
9/8/24 • 12:00 PM
Bet placement Stake Odds Payout (inc Stake)
9/5/24 • 11:49 AM $50.00 -125 -LOST
Tennessee Titans +4Spread10/4/24, 10:52 PM BetMGM
https://sports.ia.betmgm.com/en/sports/my-bets/settled 11/11
    """

    x = parse_mgm_pdf_inputs(extracted_text)
    print(x)