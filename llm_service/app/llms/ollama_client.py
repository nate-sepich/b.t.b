import json
import re
import time
import uuid
from datetime import datetime
from ollama import Client
import logging
import concurrent.futures

# Configure logging
logging.basicConfig(filename='parse_mgm_pdf_inputs.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize Ollama Client
client = Client(host='http://ollama:11434')
# client = Client(host='http://localhost:11434')


# Improved function to extract content from mistral model via Ollama
def generate_content_from_model(extracted_text: str) -> list:
    logging.info('Generating content from model')

    # Define the output JSON template with default values
    output_json_template = {
        "user_id": "Nate",
        "bet_id": str(uuid.uuid4()),  # Default to a new UUID
        "upload_timestamp": str(datetime.utcnow()),  # Current timestamp
        "league": None,
        "date": None,
        "away_team": None,
        "home_team": None,
        "wager_team": None,
        "bet_type": None,
        "selection": None,
        "odds": None,
        "risk": None,
        "outcome": None,
        "payout": None,
    }

    try:
        logging.info(f'Extracted text: {extracted_text}')
        # Create the enhanced prompt for the Mistral model
        prompt = f"""
        You are a highly capable model tasked with parsing betting slip information.
        Please extract the relevant information for each bet from the following text and populate a list of JSON objects based on the schema provided.

        Important Instructions:
        - Extract information sequentially:
          1. Identify the bet ID, teams, and date.
          2. Extract wager details including risk, payout, and bet type.
        - Match the fields to the correct types. For example:
          - "outcome" must be one of ['WON', 'LOST', 'PUSH', 'PENDING']. This field is CRITICAL for downstream processes.
          - "bet_type" must be one of ['Moneyline', 'Spread', 'Totals', 'Prop', 'Future', 'Other'].
        - Multiple monetary values may be present. Distinguish between "risk", "payout", and "to_win" by looking for terms like 'Stake', 'Risk', 'Payout'.
        - For monetary values, the smallest is the stake and the larger one is the payout or to_win.
        - Use the context of words like 'BET', 'PAYOUT', 'Settled' to determine appropriate values.
        - Extract all bets if there are multiple in the text.
        - Ensure each JSON object corresponds to a full betslip, do not create partial objects or objects without context directly from the provided Text.
        - Do not split details across objects.
        - Ensure each betslip ID appears only once in the output.
        - Do not duplicate bets or generate additional data beyond what is explicitly present in the text.
        - If a field cannot be found, set it to null.
        - Do not make assumptions or guess values if the information is not available.

        **Text:**
        "{extracted_text}"

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
          }}
        ]

        Please output the resulting list of JSON objects without additional commentary.
        """

        logging.info(f'Prompt sent to model: {prompt}')
        # Call the Mistral model via Ollama with the enhanced prompt
        response = client.generate(model='mistral', prompt=prompt)

        # Extract the content from the response
        content = response.get('response', '')
        logging.info(f'Response from model: {content}')
        
        # Try parsing the response
        try:
            parsed_data = json.loads(content)
        except json.JSONDecodeError:
            # If we encounter extra data or malformed JSON, try extracting valid JSON parts
            json_blocks = re.findall(r'\{.*?\}', content, re.DOTALL)
            if json_blocks:
                cleaned_content = json_blocks[0]  # Take the first valid JSON block
                parsed_data = json.loads(cleaned_content)
            else:
                raise ValueError("No valid JSON found in the response.")

        logging.info(f'Parsed data: {parsed_data}')
        return parsed_data

    except Exception as e:
        logging.error(f"Error generating content from model: {e}")
        return []
    
# Function to validate and correct the model output
def validate_and_correct_output(parsed_data: dict, original_text: str) -> dict:
    logging.info('Validating and correcting output')
    critical_fields = ["bet_id", "bet_type", "risk", "odds", "away_team", "home_team", "date"]

    # Ensure parsed_data is a dictionary
    if not isinstance(parsed_data, dict):
        logging.error('Expected a dictionary but got %s', type(parsed_data).__name__)
        raise ValueError(f"Expected a dictionary but got {type(parsed_data).__name__}")

    for field in critical_fields:
        if parsed_data.get(field) is None:
            # Attempt fallback extraction
            parsed_data[field] = extract_fallback_field(field, original_text)

    # Convert fields to the correct types
    if parsed_data.get("risk"):
        parsed_data["risk"] = str(parsed_data["risk"])
    if parsed_data.get("to_win"):
        parsed_data["to_win"] = str(parsed_data["to_win"])
    if parsed_data.get("payout"):
        parsed_data["payout"] = str(parsed_data["payout"])
    if parsed_data.get("profit_loss"):
        try:
            parsed_data["profit_loss"] = float(parsed_data["profit_loss"])
        except ValueError:
            parsed_data["profit_loss"] = None

    logging.info('Validated and corrected output: %s', parsed_data)
    return parsed_data

# Fallback extraction function using regex
def extract_fallback_field(field_name: str, text: str) -> str:
    logging.info('Extracting fallback field for %s', field_name)
    # Define context-based regex for different fields
    if field_name == "risk":
        match = re.search(r'(Stake\s+|\bRisk\b)\$?(\d+(\.\d{2})?)', text, re.IGNORECASE)
    elif field_name == "to_win":
        match = re.search(r'Payout\s+\(inc Stake\)\s+\$?(\d+(\.\d{2})?)', text, re.IGNORECASE)
    elif field_name == "payout":
        match = re.search(r'Payout\s+\$?(\d+(\.\d{2})?)', text, re.IGNORECASE)
    elif field_name in ["away_team", "home_team"]:
        teams = re.findall(r'\b[A-Z][a-z]+\s(?:[A-Z][a-z]+\s)*[A-Z][a-z]+\b', text)  # Match team names
        if teams:
            return teams[0] if field_name == "away_team" else (teams[1] if len(teams) > 1 else None)
    else:
        match = None

    return match.group(2) if match else None

# Function to split context into manageable batches while avoiding splits within betslips
def split_context_for_batches(text: str, max_chunk_size: int = 15) -> list:
    logging.info('Splitting context into batches')
    def chunk_text_safely(text, chunk_size):
        # Regex pattern to match the start of a betslip, taking into account variations like whitespace or special characters
        betslip_pattern = re.compile(r"(Betslip ID: \w+)", re.IGNORECASE)
        chunks = []
        current_chunk = ""

        # Iterate through the lines of the text
        for line in text.splitlines():
            if betslip_pattern.match(line):
                # If adding the current line exceeds the chunk size, start a new chunk
                if len(current_chunk) + len(line) > chunk_size and current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = line
                else:
                    # Otherwise, continue adding to the current chunk
                    if current_chunk:
                        current_chunk += "\n"
                    current_chunk += line
            else:
                current_chunk += "\n" + line

        # Append the last chunk if it's not empty
        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    batches = []
    chunks = chunk_text_safely(text, max_chunk_size)

    for i in range(0, len(chunks), 2):
        chunk_group = chunks[i:i+2]
        combined_chunk = "\n\n".join(chunk_group)
        
        # Adjust the prompt to request JSON objects with 'bet_id' and 'context'
        prompt = f"""
        Extract the following text into a list of JSON objects. Each object should contain:
        - "bet_id": The unique identifier of the betslip.
        - "context": The entire text of the betslip.

        Ensure each JSON object corresponds to a full betslip, and do not split details across batches. Respond without additional commentary.

        Text:
        {combined_chunk}
        """
        
        logging.info(f'Prompt for batch: {prompt}')
        # Call the mistral model via Ollama
        response = client.generate(model='mistral', prompt=prompt)
        
        content = response.get('response', '')
        # Clean up the response content by removing markdown formatting
        cleaned_content = content.replace("```json", "").replace("```", "").strip()
        logging.info(f'Cleaned content for batch: {cleaned_content}')

        try:
            # Try to parse the content into a list of JSON objects
            parsed_batch = json.loads(cleaned_content)
            batches.extend(parsed_batch)
        except json.JSONDecodeError as e:
            logging.error('Error decoding JSON response: %s', e)
            continue

    logging.info('Split context into batches: %s', batches)
    return batches

# Main function to parse MGM PDF inputs
def parse_mgm_pdf_inputs(extracted_text: str):
    logging.info('Parsing MGM PDF inputs')
    text_segments = split_context_for_batches(extracted_text)
    all_data = []

    # Split text_segments into groups of 3
    segment_groups = [text_segments[i:i + 3] for i in range(0, len(text_segments), 3)]

    # Parallelized code with two concurrent calls at a time
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future_to_segment_group = {executor.submit(generate_content_from_model, json.dumps(segment_group)): segment_group for segment_group in segment_groups}

        total_segments = len(segment_groups)
        completed_segments = 0
        in_progress_segments = total_segments
        waiting_segments = 0

        logging.info(f'Total segments: {total_segments}, In-progress: {in_progress_segments}, Waiting: {waiting_segments}')

        for future in concurrent.futures.as_completed(future_to_segment_group):
            segment_group = future_to_segment_group[future]
            try:
                parsed_data = future.result()
                logging.info('Parsed Bet Data: %s', parsed_data)
                all_data.extend(parsed_data)
                completed_segments += 1
                in_progress_segments -= 1
                waiting_segments = total_segments - completed_segments - in_progress_segments
                logging.info(f'Completed: {completed_segments}, In-progress: {in_progress_segments}, Waiting: {waiting_segments}')
            except Exception as e:
                logging.error('Error processing segment group %s: %s', segment_group, e)
                in_progress_segments -= 1
                waiting_segments = total_segments - completed_segments - in_progress_segments
                logging.info(f'Completed: {completed_segments}, In-progress: {in_progress_segments}, Waiting: {waiting_segments}')

    # Check if the number of text segments matches the number of output bets
    num_segments = len(text_segments)
    num_output_bets = len(all_data)
    if num_segments != num_output_bets:
        logging.warning('Mismatch between number of text segments (%d) and output bets (%d)', num_segments, num_output_bets)
    else:
        logging.info('Number of text segments matches the number of output bets')

    logging.info('All parsed data: %s', all_data)
    return all_data


# Example test call to mimic behavior with Ollama
if __name__ == "__main__":
    extracted_text = """ 
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
 Denver Broncos +6.5Spread10/6/24, 1:21 PM BetMGM
 https://sports.ia.betmgm.com/en/sports/my-bets/settled 8/139/18/24
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
 New York Giants +1.5Spread10/6/24, 1:21 PM 
"""
    start_time = time.time()
    logging.info('Start time: %s', start_time)
    try:
        x = parse_mgm_pdf_inputs(extracted_text)
        logging.info('Parsed data: %s', x)
    except Exception as e:
        logging.error('Error occurred: %s', str(e))
    finally:
        end_time = time.time()
        logging.info('End time: %s', end_time)
        logging.info('Time elapsed: %s seconds', end_time - start_time)