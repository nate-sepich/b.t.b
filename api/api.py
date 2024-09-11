from fastapi import FastAPI, UploadFile, File
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import requests
import os

app = FastAPI()

# New endpoint to handle image upload and OCR processing
@app.post("/upload/")
async def upload_image(file: UploadFile = File(...)):
    # Read the file content
    file_content = await file.read()

    try:
        # Send the file to the OCR service
        response = requests.post(
            "http://localhost:9111/ocr",
            files={"file": (file.filename, file_content, file.content_type)}
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return {"error": f"Error in OCR service: {str(e)}"}
    
    # Parse the response from the OCR service
    ocr_result = response.json()
    extracted_text = ocr_result.get("extracted_text", "")

    # try:
    #     # Update Google Sheets with the extracted text
    #     update_google_sheet([[extracted_text]])
    # except Exception as e:
    #     return {"error": f"Failed to update Google Sheets: {str(e)}"}

    return {"extracted_text": extracted_text}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, port=9000)