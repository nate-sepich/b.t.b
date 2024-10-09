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

# Preprocessing function to clean OCR text
def preprocess_text(text: str) -> str:
    logging.info('Preprocessing text')
    # Replace 'S' followed by a number with '$'
    text = re.sub(r'S(?=\d)', '$', text)

    # Correct 'Ist' to '1st'
    text = text.replace('Ist', '1st')

    # Replace underscores with commas
    text = text.replace('_', ',')

    logging.info('Preprocessed text: %s', text)
    return text

# Improved function to extract content from mistral model via Ollama
def generate_content_from_model(extracted_text: str) -> list:
    logging.info('Generating content from model')
    output_json_template = {
        "user_id": "Nate",
        "bet_id": str(uuid.uuid4()),
        "upload_timestamp": str(datetime.utcnow()),
        "league": None,
        "date": None,
        "away_team": None,
        "home_team": None,
        "wager_team": None,
        "bet_type": None,
        "odds": None,
        "risk": None,
        "to_win": None,
        "outcome": None,
    }

    try:
        # Preprocess the extracted text
        cleaned_text = preprocess_text(extracted_text)

        # Create the prompt for the mistral model
        prompt = f"""
        Extract the relevant information for each bet from the following text and populate a list of JSON objects using this schema:
        
        **Schema:**
        {json.dumps(output_json_template, indent=2)}
        
        **Text:**
        "{cleaned_text}"

        Please output the resulting list of JSON objects without additional commentary.
        """
        
        # Call the mistral model via Ollama
        response = client.generate(model='mistral', prompt=prompt)
        
        # Extract the content from the response
        content = response.get('response', '')
        
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

    except Exception as e:
        logging.error('Failed to get a response from the model: %s', str(e))
        raise RuntimeError(f"Failed to get a response from the model: {str(e)}")

    # Ensure we have a list of dictionaries before proceeding
    if not isinstance(parsed_data, list):
        logging.error('Expected a list of dictionaries but got %s', type(parsed_data).__name__)
        raise ValueError(f"Expected a list of dictionaries but got {type(parsed_data).__name__}")

    # Validate parsed data to ensure critical fields are populated
    validated_data = [validate_and_correct_output(bet, cleaned_text) for bet in parsed_data]

    logging.info('Generated content: %s', validated_data)
    return validated_data

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
    if field_name in ["risk", "to_win", "payout"]:
        match = re.search(r'\$\d+(\.\d{2})?', text)
        if match:
            return match.group().replace('$', '')
    elif field_name in ["away_team", "home_team"]:
        teams = re.findall(r'\b[A-Z]{3,}\s[A-Za-z]+\b', text)
        if teams:
            if field_name == "away_team":
                return teams[0]
            elif len(teams) > 1:
                return teams[1]
    return None

# Function to split context into manageable batches while avoiding splits within betslips
def split_context_for_batches(text: str, max_chunk_size: int = 100) -> list:
    logging.info('Splitting context into batches')
    def chunk_text_safely(text, chunk_size):
        betslip_pattern = re.compile(r"(Betslip ID: \w+)", re.IGNORECASE)
        chunks = []
        current_chunk = ""
        for line in text.splitlines():
            if betslip_pattern.match(line) and len(current_chunk) + len(line) > chunk_size:
                chunks.append(current_chunk)
                current_chunk = line  # Start a new chunk
            else:
                current_chunk += "\n" + line

        if current_chunk:
            chunks.append(current_chunk)
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
        
        # Call the mistral model via Ollama
        response = client.generate(model='mistral', prompt=prompt)
        
        content = response.get('response', '')
        # Clean up the response content by removing markdown formatting
        cleaned_content = content.replace("```json", "").replace("```", "").strip()
        logging.info('Cleaned content: %s', cleaned_content)

        try:
            # Try to parse the content into a list of JSON objects
            parsed_batch = json.loads(cleaned_content)
            batches.extend(parsed_batch)
        except json.JSONDecodeError as e:
            logging.error('Error decoding JSON response: %s', e)
            continue

    logging.info('Split context into batches: %s', batches)
    return batches

# Function to process each batch using Ollama mistral model
def parse_bet_data_with_gemma_model(batch: str) -> dict:
    logging.info('Parsing bet data with Gemma model')
    prompt = f"""
    You will now process the following batch of bet information:

    **Batch Segment:**
    "{batch}"

    Extract bet details in JSON format using the following schema, respond without additional commentary:
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
    # Call the mistral model via Ollama
    response = client.generate(model='mistral', prompt=prompt)
    content = response.get('response', '')
    try:
        parsed_data = json.loads(content)
        logging.info('Parsed data: %s', parsed_data)
        return parsed_data
    except json.JSONDecodeError as e:
        logging.error('Error decoding JSON response: %s', e)
        return {}

# Main function to parse MGM PDF inputs
def parse_mgm_pdf_inputs(extracted_text: str):
    logging.info('Parsing MGM PDF inputs')
    text_segments = split_context_for_batches(extracted_text)
    all_data = []

    # Split text_segments into groups of 5
    segment_groups = [text_segments[i:i + 5] for i in range(0, len(text_segments), 5)]

    # Parallelized code with two concurrent calls at a time
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future_to_segment_group = {executor.submit(generate_content_from_model, json.dumps(segment_group)): segment_group for segment_group in segment_groups}

        for future in concurrent.futures.as_completed(future_to_segment_group):
            segment_group = future_to_segment_group[future]
            try:
                parsed_data = future.result()
                logging.info('Parsed Bet Data: %s', parsed_data)
                all_data.extend(parsed_data)
            except Exception as e:
                logging.error('Error processing segment group %s: %s', segment_group, e)

    logging.info('All parsed data: %s', all_data)
    return all_data


# Example test call to mimic behavior with Ollama
if __name__ == "__main__":
    extracted_text = """My Bets
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
Clemson -22.5Spread"""
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
