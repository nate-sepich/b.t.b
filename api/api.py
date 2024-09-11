from fastapi import FastAPI, UploadFile, File
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import requests
import os

app = FastAPI()

# Google Sheets setup (use the actual spreadsheet ID)
SPREADSHEET_ID = 'your_actual_spreadsheet_id'
RANGE_NAME = 'Sheet1!A1'

# Function to update Google Sheets
def update_google_sheet(values):
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', ['https://www.googleapis.com/auth/spreadsheets'])
    
    # Refresh the token if it's expired
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    # Build the Sheets API service
    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()

    # Prepare the request body
    body = {'values': values}

    try:
        # Update Google Sheets
        sheet.values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=RANGE_NAME,
            valueInputOption='RAW',
            body=body
        ).execute()
    except Exception as e:
        raise Exception(f"Failed to update Google Sheets: {str(e)}")

# New endpoint to handle image upload and OCR processing
@app.post("/upload/")
async def upload_image(file: UploadFile = File(...)):
    # Read the file content
    file_content = await file.read()

    try:
        # Send the file to the OCR service
        response = requests.post(
            "http://localhost:5000/ocr",
            files={"file": (file.filename, file_content, file.content_type)}
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return {"error": f"Error in OCR service: {str(e)}"}
    
    # Parse the response from the OCR service
    ocr_result = response.json()
    extracted_text = ocr_result.get("extracted_text", "")

    try:
        # Update Google Sheets with the extracted text
        update_google_sheet([[extracted_text]])
    except Exception as e:
        return {"error": f"Failed to update Google Sheets: {str(e)}"}

    return {"extracted_text": extracted_text}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, port=9000)