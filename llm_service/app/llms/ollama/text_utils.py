import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

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
def split_context_for_batches(text: str, max_chunk_size: int = 10) -> list:
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
        batches.append(combined_chunk)

    logging.info('Split context into batches: %s', batches)
    return batches