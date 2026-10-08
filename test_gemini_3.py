import sys
import os

# Add modules directory to path
sys.path.append(os.path.join(os.getcwd(), 'modules'))

from gemini_api import generate_content

def test_model():
    print("Testing Gemini 3.1 Flash Lite connectivity...")
    try:
        response = generate_content("Hello! Please introduce yourself and confirm your model version if possible.")
        print("\nAPI Response:")
        print("-" * 20)
        print(response)
        print("-" * 20)
        print("\nSuccess: Model responded successfully.")
    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    test_model()
