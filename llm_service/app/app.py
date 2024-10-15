# External Python Dependencies
from dotenv import load_dotenv
from fastapi import FastAPI
# Internal Python Dependencies
from llms.ollama.client import generate_content_from_model
from service_models.models import LLMRequestModel, BetExtractionDetails
load_dotenv()

app = FastAPI()

# LLM Parsing Endpoint
@app.post('/llm')
async def llm(llm_request: LLMRequestModel):
    extracted_text = llm_request.extracted_text

    try:
        parsed_data = generate_content_from_model(extracted_text,list(BetExtractionDetails.model_fields.keys().__iter__()))
    except Exception as e:
        return {"error": str(e)}

    return parsed_data

# LLM Parsing Endpoint
# @app.post('/llm-extraction/mgm')
# async def llm(llm_request: LLMRequestModel):
#     extracted_text = llm_request.extracted_text

#     try:
#         parsed_data = parse_mgm_pdf_inputs(extracted_text, list(BetExtractionDetails.model_fields.keys().__iter__()))
# # ['bet_id', 'outcome', 'away_team', 'home_team', 'date', 'stake', 'risk', 'payout','league','bet_type','selection','odds','wager_team','status'])
#     except Exception as e:
#         return {"error": str(e)}

#     return parsed_data

# if __name__ == '__main__':
#     import uvicorn
#     uvicorn.run(app, port=9002)
