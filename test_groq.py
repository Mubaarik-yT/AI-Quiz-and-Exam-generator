import sys
import os

# Add current dir to path
sys.path.append(os.path.dirname(__file__))

from app import call_groq

try:
    print("Testing call_groq with mixtral...")
    res = call_groq(
        "You are a quiz generator. Output ONLY valid JSON.",
        "Generate 1 simple mcq about space. Format: {\"questions\": [{\"question\": \"...\", \"options\": [...], \"correctAnswer\": \"...\", \"explanation\": \"...\"}]}"
    )
    print("SUCCESS!")
    print(res)
except Exception as e:
    print("FAILED!")
    print(str(e))
