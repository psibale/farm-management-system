# routes/ai_routes.py

from flask import Blueprint, render_template, request, jsonify
from modules.ai_farm_manager import ai_answer_query

ai_bp = Blueprint('ai', __name__, url_prefix='/ai')


# -------------------------------
# 1️⃣ Full AI Assistant Page
# -------------------------------
@ai_bp.route('/assistant', methods=['GET', 'POST'])
def ai_assistant():
    question = None
    answer = None

    if request.method == 'POST':
        question = request.form.get('question', '').strip()
        if question:
            answer = ai_answer_query(question)

    return render_template("ai_assistant.html", question=question, answer=answer)


# -------------------------------
# 2️⃣ JSON API endpoint (for modal / AJAX)
# -------------------------------
@ai_bp.route('/query', methods=['POST'])
def ai_query():
    data = request.get_json() or {}
    question = data.get("question", "").strip()

    if not question:
        return jsonify({"answer": "❌ No question provided."})

    # Use your already working function
    answer = ai_answer_query(question)

    return jsonify({"answer": answer})
