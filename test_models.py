import requests
import os

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "YOUR_GROQ_API_KEY")
HEADERS = {"Authorization": f"Bearer {GROQ_API_KEY}"}

response = requests.get("https://api.groq.com/openai/v1/models", headers=HEADERS)
if response.ok:
    models = response.json().get("data", [])
    for m in models:
        print(m["id"])
else:
    print("Error:", response.text)
