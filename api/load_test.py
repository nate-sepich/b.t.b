import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# Number of concurrent requests to send
num_requests = 4

# File path to the image
file_path = r"C:\Users\Nate\Documents\GitRepo\b.t.b\test_images\test1.jpg"

# URL of the OCR endpoint
url = "http://localhost:9111/ocr"

def send_request():
    with open(file_path, "rb") as f:
        files = {"file": f}
        response = requests.post(url, files=files)
        return response

def main():
    responses = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(send_request) for _ in range(num_requests)]
        for future in as_completed(futures):
            responses.append(future.result())

    # Check that all responses are successful
    for response in responses:
        if response.status_code == 200:
            print(response.json())
        else:
            print(f"Request failed with status code {response.status_code}")

if __name__ == "__main__":
    main()