import google.generativeai as genai
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Configure the Google Generative AI client
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY environment variable not set")
genai.configure(api_key=api_key)

# Define a test function for the model call
def test_model_call():
    try:
        # Initialize the model
        model = genai.GenerativeModel('gemini-1.5-flash')

        # Define a test prompt
        prompt = """
        Extract the relevant information from the following text:
        "On 2023-09-13, a bet was placed on the NFL game between the Kansas City Chiefs and Los Angeles Chargers. 
        The wager was on the Chiefs with odds of 1.95, a bet amount of $100, and a payout of $195 if the Chiefs win."
        Provide a JSON object with the relevant bet details.
        """

        # Make the call to the model and generate content
        response = model.generate_content(prompt)
        print(response.text)

        # Print the response for debugging
        print("API Response:", response)

        # Return the response content
        return response

    except Exception as e:
        print(f"An error occurred: {e}")

# Call the test function
if __name__ == "__main__":
    result = test_model_call()
    print("Result:", result)