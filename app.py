"""
SmartExam AI - Flask Backend
Powered by Groq API (qwen/qwen3-32b)
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import os

app = Flask(__name__)
CORS(app)

# ==================== CONFIGURATION ====================
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "YOUR_GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "qwen/qwen3-32b"

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {GROQ_API_KEY}"
}


# ==================== HELPER: CALL GROQ API ====================
def call_groq(system_prompt: str, user_prompt: str, max_tokens: int = 4000) -> dict:
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.5,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"}
    }

    response = requests.post(GROQ_API_URL, headers=HEADERS, json=payload, timeout=60)

    if not response.ok:
        error_data = response.json()
        raise Exception(error_data.get("error", {}).get("message", f"API error {response.status_code}"))

    data = response.json()
    content = data["choices"][0]["message"]["content"].strip()

    # Strip markdown fences if present
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]

    return json.loads(content.strip())


# ==================== ROUTES ====================

@app.route("/api/health", methods=["GET"])
def health():
    """Health check and API connectivity test."""
    try:
        result = call_groq(
            "Respond only with valid JSON: {\"status\": \"ok\"}",
            "ping",
            max_tokens=20
        )
        return jsonify({"status": "connected", "model": GROQ_MODEL, "groq": result})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/generate/topic", methods=["POST"])
def generate_from_topic():
    """Generate quiz questions from a topic."""
    body = request.get_json()
    topic = body.get("topic", "").strip()
    difficulty = body.get("difficulty", "medium")
    count = int(body.get("count", 5))
    include_mcq = body.get("include_mcq", True)
    include_tf = body.get("include_tf", True)
    include_short = body.get("include_short", True)

    if not topic or len(topic) < 3:
        return jsonify({"error": "Topic is too short. Please be more specific."}), 400

    types = []
    if include_mcq:
        types.append("multiple-choice")
    if include_tf:
        types.append("true-false")
    if include_short:
        types.append("short-answer")

    if not types:
        return jsonify({"error": "Please select at least one question type."}), 400

    system_prompt = (
        "You are an expert quiz generator. Generate accurate, clear quiz questions "
        "about the specified topic. Always respond with valid JSON only. No markdown, no explanation."
    )

    user_prompt = f"""Generate exactly {count} quiz questions about: "{topic}".
Difficulty: {difficulty}
Types to use: {', '.join(types)}

Rules:
- ALL questions must be directly about "{topic}"
- Easy: basic recall, Medium: understanding, Hard: analysis/application
- MCQ: exactly 4 options (A) B) C) D)), one correct answer
- True-False: options ["True", "False"]
- Short-answer: no options, provide a model answer
- Include a brief explanation for each answer

Return ONLY valid JSON in this exact format:
{{
  "questions": [
    {{
      "id": 1,
      "type": "mcq",
      "question": "Question text here",
      "options": ["A) option", "B) option", "C) option", "D) option"],
      "correctAnswer": "A) option",
      "explanation": "Brief explanation"
    }},
    {{
      "id": 2,
      "type": "true-false",
      "question": "Statement here",
      "options": ["True", "False"],
      "correctAnswer": "True",
      "explanation": "Brief explanation"
    }},
    {{
      "id": 3,
      "type": "short-answer",
      "question": "Question here",
      "options": [],
      "correctAnswer": "Model answer here",
      "explanation": "Brief explanation"
    }}
  ]
}}"""

    try:
        data = call_groq(system_prompt, user_prompt)
        questions = data.get("questions", [])
        if not questions:
            return jsonify({"error": "AI returned no questions. Please try a different topic."}), 500
        return jsonify({"questions": questions, "count": len(questions)})
    except json.JSONDecodeError:
        return jsonify({"error": "Failed to parse AI response. Please try again."}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/generate/content", methods=["POST"])
def generate_from_content():
    """Generate quiz questions from pasted/uploaded text content."""
    body = request.get_json()
    content = body.get("content", "").strip()
    difficulty = body.get("difficulty", "medium")
    count = int(body.get("count", 5))

    if not content or len(content) < 50:
        return jsonify({"error": "Content is too short. Please provide at least 50 characters."}), 400

    word_count = len(content.split())
    if word_count < 10:
        return jsonify({"error": "Please provide at least 10 words of study material."}), 400

    # Truncate very long content
    truncated = content[:6000] + "\n[...content continues...]" if len(content) > 6000 else content

    system_prompt = (
        "You are an expert quiz generator. Read the provided material carefully. "
        "Generate questions STRICTLY based on the provided content. "
        "Do NOT ask about topics not in the material. "
        "Every answer must be found in or directly inferred from the text. "
        "Always respond with valid JSON only. No markdown."
    )

    user_prompt = f"""STUDY MATERIAL:
\"\"\"
{truncated}
\"\"\"

Based STRICTLY on the above material, generate exactly {count} quiz questions at {difficulty} difficulty.
Mix question types: multiple-choice (mcq), true-false, short-answer.

CRITICAL RULES:
- ONLY use information from the provided material
- Do NOT make up facts not in the material
- Answers MUST be verifiable from the text
- Reference the material in explanations

Return ONLY valid JSON:
{{
  "questions": [
    {{
      "id": 1,
      "type": "mcq",
      "question": "Question from material",
      "options": ["A) option", "B) option", "C) option", "D) option"],
      "correctAnswer": "A) option",
      "explanation": "Where/how this is found in the material"
    }}
  ]
}}"""

    try:
        data = call_groq(system_prompt, user_prompt)
        questions = data.get("questions", [])
        if not questions:
            return jsonify({"error": "AI could not generate questions. Try with more detailed material."}), 500
        return jsonify({"questions": questions, "count": len(questions)})
    except json.JSONDecodeError:
        return jsonify({"error": "Failed to parse AI response. Try with different content."}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== MAIN ====================
if __name__ == "__main__":
    print("🧠 SmartExam AI Backend Starting...")
    print(f"🔑 Groq API Key: {GROQ_API_KEY[:12]}...")
    print(f"🤖 Model: {GROQ_MODEL}")
    print("🌐 Server: http://localhost:5000")
    app.run(debug=True, port=5000)
