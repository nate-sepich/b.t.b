# External Python Dependencies
import json
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File
import requests
# Internal Python Dependencies
from service_models.models import LLMRequestModel, BetDetails

app = FastAPI()

# Image Upload and OCR Processing
@app.post("/upload/")
async def upload_image(file: UploadFile = File(...)):
    file_content = await file.read()

    try:
        # Send the file to the OCR service
        response = requests.post(
            "http://172.17.0.1:9000/ocr",
            files={"file": (file.filename, file_content, file.content_type)}
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return {"error": f"Error in OCR service: {str(e)}"}

    try:
        # Parse the extracted text into the Pydantic object for the /llm call
        response_json = response.json()
        llmRequest = LLMRequestModel(extracted_text=response_json["extracted_text"])
    except Exception as e:
        return {"error": f"Error parsing OCR response: {str(e)}"}

    try:
        # Send the request to the LLM service
        response = requests.post(
            "http://172.17.0.1:9002/llm",
            data=llmRequest.json()
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return {"error": f"Error in LLM service: {str(e)}"}

    try:
        # Parse the LLM response into a list of Pydantic BetDetails models
        response_json = response.json()
        print(response_json)
        betsRequest = [BetDetails(**bet) for bet in response_json]

    except Exception as e:
        return {"error": f"Error parsing LLM response: {str(e)}"}

    try:
        # Convert the list of BetDetails objects to a list of dictionaries
        betsRequestDicts = [bet.dict() for bet in betsRequest]
        
        # Convert the list of dictionaries to a JSON string
        betsRequestJson = json.dumps(betsRequestDicts, default=str)
        
        # Send the parsed data to the Storage service
        response = requests.post(
            "http://172.17.0.1:9004/bets",
            data=betsRequestJson,
            headers={'Content-Type': 'application/json'}
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return {"error": f"Error in Bets service: {str(e)}"}

    return response.json()

# Betting Data Text Ingestion for ESPN Exports
@app.post("/exports/espn/")
async def parse_espn_bet_text(bet_data: str):
    try:
        # Parse the extracted text into the Pydantic object for the /llm call
        llmRequest = LLMRequestModel(extracted_text=bet_data)
    except Exception as e:
        return {"error": f"Error parsing OCR response: {str(e)}"}

    try:
        # Send the request to the LLM service
        response = requests.post(
            "http://172.17.0.1:9002/llm",
            data=llmRequest.json()
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return {"error": f"Error in LLM service: {str(e)}"}

    try:
        # Parse the LLM response into a list of Pydantic BetDetails models
        response_json = response.json()
        print(response_json)
        betsRequest = [BetDetails(**bet) for bet in response_json]

    except Exception as e:
        return {"error": f"Error parsing LLM response: {str(e)}"}

    try:
        # Convert the list of BetDetails objects to a list of dictionaries
        betsRequestDicts = [bet.dict() for bet in betsRequest]
        
        # Convert the list of dictionaries to a JSON string
        betsRequestJson = json.dumps(betsRequestDicts, default=str)
        
        # Send the parsed data to the Storage service
        response = requests.post(
            "http://172.17.0.1:9004/bets",
            data=betsRequestJson,
            headers={'Content-Type': 'application/json'}
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return {"error": f"Error in Bets service: {str(e)}"}

    return response.json()


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, port=9001)
