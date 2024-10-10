from PyPDF2 import PdfReader
from io import BytesIO
import re
from datetime import datetime

# File path for the uploaded PDF
pdf_file_path = "BetMGM.pdf"

class IngestionProvider:
    # Function to extract text using PyPDF2
    def extract_text_pypdf2(file: bytes) -> str:
        try:
            pdf_stream = BytesIO(file)
            reader = PdfReader(pdf_stream)
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()  # Extract text from each page
                page_text = IngestionProvider.cleanup_text(page_text)
                text += page_text
            return text
        except Exception as e:
            return f"Error using PyPDF2: {e}"

    @staticmethod
    def cleanup_text(text: str) -> str:
        # Remove footers containing the specific URL
        text = re.sub(r'https://sports\.ia\.betmgm\.com/en/sports/my-bets/settled \d+/\d+', '', text)
        
        # Remove headers containing a datetime with BetMGM at the end
        text = re.sub(r'\d{1,2}/\d{1,2}/\d{2}, \d{1,2}:\d{2} (AM|PM) BetMGM', '', text)
        
        return text

if __name__ == "__main__":
    # Read the PDF file as bytes
    with open(pdf_file_path, "rb") as file:
        pdf_bytes = file.read()
    print(IngestionProvider.extract_text_pypdf2(pdf_bytes))

    