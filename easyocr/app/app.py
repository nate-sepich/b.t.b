from flask import Flask, request, jsonify
import easyocr
import io
from PIL import Image
import numpy as np

app = Flask(__name__)
reader = easyocr.Reader(['en'])

@app.route('/ocr', methods=['POST'])
def ocr():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    # Read the file and convert to a format that EasyOCR can understand (bytes or numpy array)
    image_bytes = file.read()  # Read the file as bytes
    image = Image.open(io.BytesIO(image_bytes))  # Open the image with PIL
    image_np = np.array(image)  # Convert the image to a numpy array

    # Process the image using EasyOCR
    result = reader.readtext(image_np)  # Pass the numpy array to EasyOCR

    # Extract text from the result
    extracted_text = " ".join([text[1] for text in result])
    
    return jsonify({'extracted_text': extracted_text})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9111)
