import os
import json
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Check if GOOGLE_API_KEY is set
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY environment variable not set")

# Configure the Google Generative AI client
genai.configure(api_key=api_key)

def generate_content_from_model(extracted_text: str, output_json: dict) -> dict:
    try:
        # Initialize the model
        model = genai.GenerativeModel('gemini-1.5-flash')

        # Prompt structure to guide the model
        prompt = f"""
        Extract relevant information from the following text and populate the provided JSON object:
        
        Text: "{extracted_text}"
        Template: {json.dumps(output_json, indent=2)}
        
        Ensure the JSON object is valid and only fills in one object based on the text. If data is missing or unclear, leave the field blank or null.
        """
        
        # Generate content from LLM
        response = model.generate_content(prompt)
        
        # Extract the content from the response object (adjust this based on actual response structure)
        if hasattr(response, 'text'):
            content = response.text
        else:
            content = str(response)
            
        # Clean up the response content by removing markdown formatting
        cleaned_content = content.replace("```json", "").replace("```", "").strip()
            
    except Exception as e:
        raise RuntimeError(f"Failed to get a response from LLM: {str(e)}")
    
    # Handling response and JSON parsing
    try:
        # Attempt to parse the cleaned response content as JSON
        parsed_data = json.loads(cleaned_content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse the response as JSON: {str(e)}")
    
    return parsed_data