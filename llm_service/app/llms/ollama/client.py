import json
import os
import re
import time
import uuid
from datetime import datetime
from ollama import Client
import logging
import concurrent.futures
import subprocess
from llms.ollama.text_utils import extract_fallback_field, split_context_for_batches
import random

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize Ollama Client with FP16 precision to reduce memory usage
btb_ollama_model = os.getenv('BTB_OLLAMA_MODEL', 'mistral')
btb_ollama_model_keep_alive = os.getenv('OLLAMA_KEEP_ALIVE', '1h')

logging.info(f'Pulling Ollama Model: {btb_ollama_model}')
client = Client(host='http://ollama:11434')
logging.info(f'Model Pull Status: {client.pull(btb_ollama_model)}')
sample = client.generate(model=btb_ollama_model, prompt='Hello! Respond with only Hello.',keep_alive=btb_ollama_model_keep_alive)
logging.info(f'Model Available for {btb_ollama_model_keep_alive}: {sample})')

# Function to monitor GPU usage
def log_gpu_usage():
    try:
        result = subprocess.run(['nvidia-smi'], stdout=subprocess.PIPE, text=True)
        logging.info(f'GPU Status: {result.stdout}')
    except Exception as e:
        logging.error(f'Error retrieving GPU status: {e}')

# Retry decorator with exponential backoff
def retry_with_backoff(retries=3, backoff_in_seconds=1):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    wait = backoff_in_seconds * (2 ** attempt) + random.uniform(0, 1)
                    logging.error(f'Error: {e}. Retrying in {wait:.2f} seconds...')
                    time.sleep(wait)
            return None
        return wrapper
    return decorator

# Improved function to extract content from Mistral model via Ollama
@retry_with_backoff(retries=3, backoff_in_seconds=2)
def generate_content_from_model(extracted_text: str, fields: list) -> list:
    logging.info('Generating content from model')

    # Define the output JSON template with default values
    output_json_template = {field: None for field in fields}

    try:
        logging.info(f'Extracted text: {extracted_text}')
        # Create the enhanced prompt for the Mistral model
        prompt = f"""
<s>[INST]
You are a highly capable model tasked with parsing betting slip information. The text may contain OCR errors.
Please extract the relevant information for each bet from the following text and populate a list of JSON objects based on the schema provided.

Important Instructions:
- Dollar signs ($) might be misread as 'S' or '5'. Make corrections where applicable. There won't be bets greater than $100, so any value above that should be assumed to be an OCR error.
- Match the fields to the correct types. For example:
    - "outcome" must be one of ['WON', 'LOST', 'PUSH', 'PENDING'].
- Multiple monetary values may be present. Distinguish between "risk", "payout", and "to_win".
- Use the context of words like 'BET', 'PAYOUT', 'Settled' to determine appropriate values.
- Dates are in the format 'MMM DD, YYYY at HH:MM AM/PM' in most cases.
- Extract all bets if there are multiple in the text.

Extract the following fields into valid JSON format:
{output_json_template}

Example Input:
Under 21 Ist Half Totals LOST Result Over 21 New Orleans Saints at Atlanta Falcons 9/29/24 12.02 PM Stake Odds Payout (inc Stake) 550.00 -130 Details

Example Output:
[
  {{
    "bet_id": null,
    "result": "Over 21",
    "league": "NFL",
    "date": "9/29/24 12:02 PM",
    "away_team": "New Orleans Saints",
    "home_team": "Atlanta Falcons",
    "wager_team": null,
    "bet_type": "Totals",
    "selection": "Under 21 Ist Half Totals",
    "odds": "-130",
    "stake": "50.00",
    "payout": "0.00",
    "outcome": "LOST"
  }}
]

Example Input:
Arkansas +5.5 Spread WON Result Arkansas +5.5 Arkansas at Texas A&M (Neutral Venue) 9/28/24 2.30 PM Stake Odds Payout (inc Stake) 515.00 -105 529.29 Details

Example Output:
[
  {{
    "bet_id": null,
    "result": "Over 21",
    "league": "NFL",
    "date": "9/29/24 12:02 PM",
    "away_team": "Arkansas",
    "home_team": "Texas A&M",
    "wager_team": null,
    "bet_type": "Spread",
    "selection": "Arkansas +5.5",
    "odds": "-105",
    "stake": "15.00",
    "payout": "29.29",
    "outcome": "WON"
  }}
]

Text:
{extracted_text}

Do not add any additional text, commentary, or formatting. Ensure the JSON is fully compliant and properly formatted.
[/INST]</s>
"""

        # logging.info(f'Prompt sent to model: {prompt}')
        # Call the Mistral model via Ollama with the enhanced prompt
        response = client.generate(model=btb_ollama_model, prompt=prompt)

        content = response.get('response', '')
        # Clean up the response content by removing markdown formatting
        cleaned_content = content.replace("<|json|>", "").replace("<|end|>", "").strip()
        # logging.info(f'Cleaned content from batch: {cleaned_content}')

        try:
            # Try to parse the content into a list of JSON objects
            parsed_data = json.loads(cleaned_content)
        except json.JSONDecodeError as e:
            logging.error('Error decoding JSON response: %s. Attempting to parse partial JSON.', e)
            parsed_data = attempt_partial_json_parsing(cleaned_content)

        logging.info(f'Parsed data: {parsed_data}')
        return parsed_data

    except Exception as e:
        logging.error(f"Error generating content from model: {e}")
        return []

# Attempt to parse partial JSON blocks if full JSON fails
def attempt_partial_json_parsing(content: str) -> list:
    try:
        json_blocks = re.findall(r'\{(?:[^{}]|(?R))*\}', content, re.DOTALL)
        parsed_data = [json.loads(block) for block in json_blocks if block]
        return parsed_data
    except json.JSONDecodeError as e:
        logging.error(f'Error decoding partial JSON content: {e}')
        return []

# Function to validate and correct the model output
def validate_and_correct_output(parsed_data: dict, original_text: str) -> dict:
    logging.info('Validating and correcting output')
    critical_fields = ["bet_id", "bet_type", "risk", "odds", "away_team", "home_team", "date"]
    
    if not isinstance(parsed_data, dict):
        logging.error('Expected a dictionary but got %s', type(parsed_data).__name__)
        raise ValueError(f"Expected a dictionary but got {type(parsed_data).__name__}")
    
    for field in critical_fields:
        if parsed_data.get(field) is None:
            extracted_value = extract_fallback_field(field, original_text)
            if extracted_value:
                parsed_data[field] = extracted_value
            else:
                logging.warning(f'Field "{field}" could not be extracted. Setting to null.')
                parsed_data[field] = None

    # Convert and validate fields as needed
    for field in ["risk", "to_win", "payout"]:
        if parsed_data.get(field):
            try:
                parsed_data[field] = str(parsed_data[field])
            except ValueError:
                logging.warning(f'Field "{field}" could not be converted to string.')
                parsed_data[field] = None

    if parsed_data.get("profit_loss"):
        try:
            parsed_data["profit_loss"] = float(parsed_data["profit_loss"])
        except ValueError:
            parsed_data["profit_loss"] = None

    logging.info('Validated and corrected output: %s', parsed_data)
    return parsed_data

# Main function to parse MGM PDF inputs
def parse_mgm_pdf_inputs(extracted_text: str, fields: list):
    logging.info('Parsing MGM PDF inputs')
    text_segments = split_context_for_batches(extracted_text)
    all_data = []

    # Split text_segments into groups of 3
    segment_groups = [text_segments[i:i + 3] for i in range(0, len(text_segments), 3)]
    total_segments = len(segment_groups)
    completed_segments = 0
    in_progress_segments = 0
    waiting_segments = total_segments
    
    # Parallelized code with a single worker to manage memory usage
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future_to_segment_group = {executor.submit(generate_content_from_model, json.dumps(segment_group), fields): segment_group for segment_group in segment_groups}

        logging.info(f'Total segments: {total_segments}, In-progress: {in_progress_segments}, Waiting: {waiting_segments}')

        for future in concurrent.futures.as_completed(future_to_segment_group):
            segment_group = future_to_segment_group[future]
            try:
                in_progress_segments += 1
                waiting_segments = total_segments - completed_segments - in_progress_segments
                logging.info(f'Completed: {completed_segments}, In-progress: {in_progress_segments}, Waiting: {waiting_segments}')
                parsed_data = future.result()
                if parsed_data:
                    logging.info('Parsed Bet Data: %s', parsed_data)
                    all_data.extend(parsed_data)
                    completed_segments += 1
                    in_progress_segments -= 1
            except Exception as e:
                logging.error('Error processing segment group %s: %s', segment_group, e)
                in_progress_segments -= 1
                waiting_segments = completed_segments - in_progress_segments
                logging.info(f'Completed: {completed_segments}, In-progress: {in_progress_segments}, Waiting: {waiting_segments}')

    # Check if the number of text segments matches the number of output bets
    num_segments = len(text_segments)
    num_output_bets = len(all_data)
    if num_segments != num_output_bets:
        logging.warning('Mismatch between number of text segments (%d) and output bets (%d)', num_segments, num_output_bets)
        logging.error('Potential data processing issue detected. Consider implementing detailed error handling to reconcile discrepancies between input segments and output bets.')
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
"""
    start_time = time.time()
    logging.info('Start time: %s', start_time)
    try:
        x = parse_mgm_pdf_inputs(extracted_text, ['bet_id', 'result', 'away_team', 'home_team', 'date', 'stake', 'odds', 'payout'])
        logging.info('Parsed data: %s', x)
    except Exception as e:
        logging.error('Error occurred: %s', str(e))
    finally:
        end_time = time.time()
        logging.info('Time elapsed: %s seconds', end_time - start_time)