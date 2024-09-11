from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import os

def check_spreadsheet_access():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', ['https://www.googleapis.com/auth/spreadsheets'])
    
    # Refresh the token if it's expired
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    # Build the Sheets API service
    service = build('sheets', 'v4', credentials=creds)
    
    try:
        sheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        print(f"Spreadsheet {SPREADSHEET_ID} found: {sheet['properties']['title']}")
    except Exception as e:
        print(f"Error accessing spreadsheet: {str(e)}")

check_spreadsheet_access()
