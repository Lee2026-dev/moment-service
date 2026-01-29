import sys
import os
sys.path.append(os.getcwd())

from dotenv import load_dotenv
load_dotenv()

from app.services.ai import generate_summary

def test_real_summary():
    print("Testing AI Summary with OpenRouter...")
    text = """
    Artificial Intelligence (AI) is intelligence demonstrated by machines, as opposed to the natural intelligence displayed by humans or animals. 
    Leading AI textbooks define the field as the study of "intelligent agents": any system that perceives its environment and takes actions that maximize its chance of achieving its goals. 
    Some popular accounts use the term "artificial intelligence" to describe machines that mimic "cognitive" functions that humans associate with the human mind, such as "learning" and "problem solving".
    """
    
    try:
        result = generate_summary(text)
        print("\n--- Success! ---")
        print(f"Summary: {result['summary']}")
        print(f"Title: {result['suggested_title']}")
    except Exception as e:
        print("\n--- Failed ---")
        print(f"Error: {e}")
        print("Check your OPENROUTER_API_KEY in .env file.")

if __name__ == "__main__":
    test_real_summary()
