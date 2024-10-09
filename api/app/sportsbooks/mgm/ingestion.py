from PyPDF2 import PdfReader
from io import BytesIO

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
                text += page.extract_text()  # Extract text from each page
            return text
        except Exception as e:
            return f"Error using PyPDF2: {e}"

if __name__ == "__main__":
    # Read the PDF file as bytes
    with open(pdf_file_path, "rb") as file:
        pdf_bytes = file.read()
    print(IngestionProvider.extract_text_pypdf2(pdf_bytes))

    