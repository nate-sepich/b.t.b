import pytest
from fastapi.testclient import TestClient
from concurrent.futures import ThreadPoolExecutor, as_completed
import io
from api import app  # Assuming the FastAPI app is in a file named api.py

client = TestClient(app)

def upload_file():
    file_path = r"C:\Users\Nate\Documents\GitRepo\b.t.b\test_images\nutrition+label+smaller-1752310982.jpg"
    with open(file_path, "rb") as f:
        file_content = io.BytesIO(f.read())
    response = client.post(
        "/upload/",
        files={"file": (file_path, file_content, "image/jpeg")}
    )
    return response

def test_upload_image_scalability():
    num_requests = 10  # Number of concurrent requests to test scalability
    responses = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(upload_file) for _ in range(num_requests)]
        for future in as_completed(futures):
            responses.append(future.result())

    # Check that all responses are successful
    for response in responses:
        assert response.status_code == 200
        assert "extracted_text" in response.json()

if __name__ == "__main__":
    pytest.main()