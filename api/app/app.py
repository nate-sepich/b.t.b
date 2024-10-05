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
        # Parse the extracted text into the pydantic object for the /llm call
        response_json = response.json()
        llmRequest = LLMRequestModel(extracted_text=response_json["extracted_text"], output_json=BetDetails.schema())
    except Exception as e:
        return {"error": f"Error parsing OCR response: {str(e)}"}
    
    try:
        # Send the file to the OCR service
        response = requests.post(
            "http://172.17.0.1:9002/llm",
            data=llmRequest.json()
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return {"error": f"Error in LLM service: {str(e)}"}
    
    try: 
        # Parse the extracted text into the pydantic object for the /bets call
        response_json = response.json()
        print(response_json)
        betsRequest = BetDetails(**response_json)
        
    except Exception as e:
        return {"error": f"Error parsing OCR response: {str(e)}"}
    
    try:
    # Send the file to the Storage service
        response = requests.post(
            "http://172.17.0.1:9004/bets",
            data=betsRequest.json()
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return {"error": f"Error in Bets service: {str(e)}"}
    
    return response.json()


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, port=9001)