# External Python Dependencies
import json
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException
import requests
import logging
import time

# Internal Python Dependencies
from service_models.models import LLMRequestModel, BetDetails
from sportsbooks.mgm.ingestion import IngestionProvider as mgm_ingestion

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

# Retry logic for requests
def retry_request(func, retries=3, delay=2):
    for attempt in range(retries):
        try:
            return func()
        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                logger.warning(f"Retrying due to: {str(e)}. Attempt {attempt + 1} of {retries}")
                time.sleep(delay)
            else:
                raise

# Validation and parsing utility
def parse_and_validate_llm_response(response):
    try:
        response_json = response.json()
        betsRequest = []
        for bet in response_json:
            try:
                bet.pop('user_id', None)  # Remove user_id if present
                betsRequest.append(BetDetails(**{**bet, 'outcome': bet.get('outcome', 'WON')},user_id='Nate'))
            except Exception as e:
                logger.warning(f"Skipping invalid bet data: {str(e)}")
                with open('failed_bets.log', 'a') as log_file:
                    log_file.write(json.dumps(bet, default=str) + '\n')
                    
        logger.info("Parsed LLM response into BetDetails models")
        return betsRequest
    except Exception as e:
        logger.error(f"Error parsing or validating LLM response data: {str(e)}")
        raise

# Image Upload and OCR Processing
@app.post("/upload/")
async def upload_image(file: UploadFile = File(...)):
    logger.info(f"Received file: {file.filename}")
    
    # File size limit check (e.g., 5MB)
    if file.spool_max_size > 5 * 1024 * 1024:
        logger.error("File size exceeds limit (5MB)")
        raise HTTPException(status_code=413, detail="File size exceeds limit (5MB)")
    
    file_content = await file.read()

    try:
        # Send the file to the OCR service
        logger.info("Sending file to OCR service")
        response = retry_request(lambda: requests.post(
            "http://easyocr:9000/ocr",
            files={"file": (file.filename, file_content, file.content_type)}
        ))
        response.raise_for_status()
        logger.info("Received response from OCR service")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error in OCR service: {str(e)}")
        return {"error": f"Error in OCR service: {str(e)}"}

    try:
        # Parse the extracted text into the Pydantic object for the /llm call
        response_json = response.json()
        llmRequest = LLMRequestModel(extracted_text=response_json["extracted_text"])
        logger.info("Parsed OCR response into LLMRequestModel")
    except Exception as e:
        logger.error(f"Error parsing OCR response: {str(e)}")
        return {"error": f"Error parsing OCR response: {str(e)}"}

    try:
        # Send the request to the LLM service
        logger.info("Sending request to LLM service")
        response = retry_request(lambda: requests.post(
            "http://llm_service:9002/llm",
            data=llmRequest.json()
        ))
        response.raise_for_status()
        logger.info("Received response from LLM service")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error in LLM service: {str(e)}")
        return {"error": f"Error in LLM service: {str(e)}"}

    try:
        # Parse and validate the LLM response
        betsRequest = parse_and_validate_llm_response(response)
    except Exception as e:
        return {"error": str(e)}

    try:
        # Convert the list of BetDetails objects to a list of dictionaries
        betsRequestDicts = [bet.dict() for bet in betsRequest]
        betsRequestJson = json.dumps(betsRequestDicts, default=str)
        logger.info("Converted BetDetails models to JSON format")

        # Send the parsed data to the Storage service
        logger.info("Sending parsed data to Storage service")
        response = retry_request(lambda: requests.post(
            "http://storage_service:9004/bets",
            data=betsRequestJson,
            headers={'Content-Type': 'application/json'}
        ))
        response.raise_for_status()
        logger.info("Successfully stored bets data")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error in Bets service: {str(e)}")
        return {"error": f"Error in Bets service: {str(e)}"}

    return response.json()

# Betting Data Text Ingestion for ESPN Exports
@app.post("/imports/espn/")
async def parse_espn_bet_text(bet_data: str):
    logger.info("Received ESPN bet data for processing")
    try:
        # Parse the extracted text into the Pydantic object for the /llm call
        llmRequest = LLMRequestModel(extracted_text=bet_data)
        logger.info("Parsed bet data into LLMRequestModel")
    except Exception as e:
        logger.error(f"Error parsing bet data: {str(e)}")
        return {"error": f"Error parsing bet data: {str(e)}"}

    try:
        # Send the request to the LLM service
        logger.info("Sending request to LLM service")
        response = retry_request(lambda: requests.post(
            "http://llm_service:9002/llm",
            data=llmRequest.json()
        ))
        response.raise_for_status()
        logger.info("Received response from LLM service")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error in LLM service: {str(e)}")
        return {"error": f"Error in LLM service: {str(e)}"}

    try:
        # Parse and validate the LLM response
        betsRequest = parse_and_validate_llm_response(response)
    except Exception as e:
        return {"error": str(e)}

    try:
        # Convert the list of BetDetails objects to a list of dictionaries
        betsRequestDicts = [bet.dict() for bet in betsRequest]
        betsRequestJson = json.dumps(betsRequestDicts, default=str)
        logger.info("Converted BetDetails models to JSON format")

        # Send the parsed data to the Storage service
        logger.info("Sending parsed data to Storage service")
        response = retry_request(lambda: requests.post(
            "http://storage_service:9004/bets",
            data=betsRequestJson,
            headers={'Content-Type': 'application/json'}
        ))
        response.raise_for_status()
        logger.info("Successfully stored bets data")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error in Bets service: {str(e)}")
        return {"error": f"Error in Bets service: {str(e)}"}

    return response.json()

# Betting Data Text Ingestion for MGM Exports
@app.post("/imports/mgm/")
async def parse_mgm_bet_pdf(file: UploadFile = File(...)):
    logger.info(f"Received MGM bet PDF file: {file.filename}")
    image_bytes = await file.read()
    
    try:
        bet_data = mgm_ingestion.extract_text_pypdf2(image_bytes)
        logger.info(f"Extracted bet data from PDF: {bet_data}")
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        return {"error": f"Error extracting text from PDF: {str(e)}"}
    
    try:
        # Parse the extracted text into the Pydantic object for the /llm call
        llmRequest = LLMRequestModel(extracted_text=bet_data)
        logger.info("Parsed bet data into LLMRequestModel")
    except Exception as e:
        logger.error(f"Error parsing bet data: {str(e)}")
        return {"error": f"Error parsing bet data: {str(e)}"}

    try:
        # Send the request to the LLM service
        logger.info("Sending request to LLM service")
        response = retry_request(lambda: requests.post(
            "http://llm_service:9002/llm-extraction/mgm",
            data=llmRequest.json()
        ))
        response.raise_for_status()
        logger.info("Received response from LLM service")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error in LLM service: {str(e)}")
        return {"error": f"Error in LLM service: {str(e)}"}

    try:
        # Parse and validate the LLM response
        betsRequest = parse_and_validate_llm_response(response)
    except Exception as e:
        return {"error": str(e)}

    try:
        # Convert the list of BetDetails objects to a list of dictionaries
        betsRequestDicts = [bet.dict() for bet in betsRequest]
        betsRequestJson = json.dumps(betsRequestDicts, default=str)
        logger.info("Converted BetDetails models to JSON format")

        # Send the parsed data to the Storage service
        logger.info("Sending parsed data to Storage service")
        response = retry_request(lambda: requests.post(
            "http://storage_service:9004/bets",
            data=betsRequestJson,
            headers={'Content-Type': 'application/json'}
        ))
        response.raise_for_status()
        logger.info("Successfully stored bets data")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error in Bets service: {str(e)}")
        return {"error": f"Error in Bets service: {str(e)}"}

    return response.json()

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, port=9001)
