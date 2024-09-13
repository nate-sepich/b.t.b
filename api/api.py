from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from typing import Optional
import requests
from gemini_client import generate_content_from_model
from storage import add_bet_to_csv, get_user_bets_csv, calculate_metrics
load_dotenv()

app = FastAPI()

class LLMRequestModel(BaseModel):
    extracted_text: str
    output_json: dict

class BetDetails(BaseModel):
    bet_type: Optional[str] = None
    league: Optional[str] = None
    date: Optional[str] = None
    away_team: Optional[str] = None
    home_team: Optional[str] = None
    wager_team: Optional[str] = None
    odds: Optional[float] = None
    bet: Optional[float] = None
    risk: Optional[float] = None
    payout: Optional[float] = None
    winning: Optional[bool] = None
    outcome: Optional[str] = None
    bankroll: Optional[float] = None
    profit_loss: Optional[float] = None

# LLM Parsing Endpoint
@app.post('/llm')
async def llm(llm_request: LLMRequestModel):
    extracted_text = llm_request.extracted_text
    output_json = llm_request.output_json

    try:
        parsed_data = generate_content_from_model(extracted_text, output_json)
        add_bet_to_csv(parsed_data)
    except Exception as e:
        return {"error": str(e)}
    
    return {"parsed_data": parsed_data}

# Image Upload and OCR Processing
@app.post("/upload/")
async def upload_image(file: UploadFile = File(...)):
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
    
    ocr_result = response.json()
    extracted_text = ocr_result.get("extracted_text", "")

    return {"extracted_text": extracted_text}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, port=9000)