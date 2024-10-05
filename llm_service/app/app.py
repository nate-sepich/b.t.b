# External Python Dependencies
from dotenv import load_dotenv
from fastapi import FastAPI
# Internal Python Dependencies
from llms.gemini_client import generate_content_from_model
from service_models.models import LLMRequestModel, LLMParsedDataResponse, BetDetails
load_dotenv()

app = FastAPI()

# LLM Parsing Endpoint
@app.post('/llm')
async def llm(llm_request: LLMRequestModel):
    extracted_text = llm_request.extracted_text
    output_json = BetDetails(**{}).dict()

    try:
        parsed_data = generate_content_from_model(extracted_text)
        print(parsed_data)
    except Exception as e:
        return {"error": str(e)}

    return parsed_data

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, port=9002)
