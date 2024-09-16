import asyncio
import httpx
import os

# Set up the endpoint and test file
URL = "http://localhost:9000/ocr"
FILE_PATH = r"C:\Users\Nate\Documents\GitRepo\b.t.b\test_images\test1.jpg"

async def upload_file(client, file_path):
    """Upload a file to the FastAPI server."""
    with open(file_path, 'rb') as file:
        files = {'file': (os.path.basename(file_path), file, 'multipart/form-data')}
        response = await client.post(URL, files=files)
        if response.status_code == 200:
            print(f"Success: {response.json()}")
        else:
            print(f"Failed with status code {response.status_code}: {response.text}")

async def run_load_test(num_requests):
    """Run multiple requests concurrently to load test the server."""
    async with httpx.AsyncClient(timeout=30) as client:
        tasks = [upload_file(client, FILE_PATH) for _ in range(num_requests)]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    # Number of requests for the load test
    num_requests = 10  # Adjust this number based on how heavy a load you want to test
    asyncio.run(run_load_test(num_requests))
