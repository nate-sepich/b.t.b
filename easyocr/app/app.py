from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import easyocr
import io
from PIL import Image
import numpy as np
import logging
import time

app = FastAPI()
reader = easyocr.Reader(['en'])

# Initialize logging to standard output
logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()])
logger = logging.getLogger(__name__)

class OCRResponse(BaseModel):
    extracted_text: str

@app.post("/ocr", response_model=OCRResponse)
async def ocr(file: UploadFile = File(...)):
    if not file:
        logger.error("No file part provided.")
        raise HTTPException(status_code=400, detail="No file part")
    
    if file.filename == '':
        logger.error("No file selected.")
        raise HTTPException(status_code=400, detail="No selected file")
    allowed_extensions = {'png', 'jpg', 'jpeg', 'bmp', 'gif'}

    filename = file.filename.lower()
    if not any(filename.endswith(ext) for ext in allowed_extensions):
        logger.error("Unsupported file type.")
        raise HTTPException(status_code=400, detail="Unsupported file type.")
    
    start_time = time.time()  # Start time for logging processing time
    
    try:
        # Read the file and convert to a format that EasyOCR can understand (bytes or numpy array)
        image_bytes = await file.read()  # Read the file as bytes
        logger.info(f"File {file.filename} read successfully.")

        image = Image.open(io.BytesIO(image_bytes))  # Open the image with PIL
        image_np = np.array(image)  # Convert the image to a numpy array
        logger.info(f"File {file.filename} successfully converted to numpy array.")

        # Process the image using EasyOCR
        result = reader.readtext(image_np)  # Pass the numpy array to EasyOCR
        logger.info(f"Text extraction completed for file {file.filename}.")

        # Extract text from the result
        extracted_text = " ".join([text[1] for text in result])
        logger.info(f"Extracted text: {extracted_text}")

        end_time = time.time()  # End time for logging processing time
        processing_time = end_time - start_time
        logger.info(f"Text extraction time for {file.filename}: {processing_time:.2f} seconds.")

        return OCRResponse(extracted_text=extracted_text)
    
    except Exception as e:
        logger.error(f"Error processing file {file.filename}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error processing the file.")

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=9000)
