# routes/ai_routes.py
from flask import Blueprint, render_template, request, jsonify
from modules.ai_farm_manager import ai_answer_query

ai_bp = Blueprint('ai', __name__, url_prefix='/ai')

@ai_bp.route('/assistant', methods=['GET', 'POST'])
def ai_assistant():
    answer = None
    if request.method == 'POST':
        question = request.form.get('question')
        if question:
            answer = ai_answer_query(question)
    return render_template('ai_assistant.html', answer=answer)

# --- NEW JSON endpoint for modal ---
@ai_bp.route('/query', methods=['POST'])
def ai_query():
    data = request.get_json()
    question = data.get('question', '').strip()

    if not question:
        return jsonify({'answer': '❌ No question provided.'})

    # Use your existing ai_answer_query function
    answer = ai_answer_query(question)
    return jsonify({'answer': answer})
