import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Check if NVIDIA_API_KEY is set
api_key = os.getenv("NVIDIA_API_KEY")
if not api_key:
    raise ValueError("NVIDIA_API_KEY environment variable not set")

# Configure the NVIDIA OpenAI client
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=api_key
)

def generate_content_from_model(prompt: str):
    try:
        completion = client.chat.completions.create(
        model="nvidia/llama-3.1-nemotron-51b-instruct",
                    messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        top_p=1,
        max_tokens=1024,
        stream=True
        )
        for chunk in completion:
            if chunk.choices[0].delta.content is not None:
                print(chunk.choices[0].delta.content, end="")
    except Exception as e:
        print(f"An error occurred: {e}")



if __name__ == "__main__":
    generate_limerick()
