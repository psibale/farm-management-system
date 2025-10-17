# routes/ai_assistant.py
from flask import Blueprint, render_template, request
from modules.ai_farm_manager import ai_answer_query

ai_bp = Blueprint('ai', __name__)

@ai_bp.route('/ai_assistant', methods=['GET', 'POST'])
def ai_assistant():
    response = None
    question = None
    if request.method == 'POST':
        question = request.form.get('question')
        if question:
            response = ai_answer_query(question)  # We'll define this in modules
    return render_template('ai_assistant.html', question=question, response=response)
