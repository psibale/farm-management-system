from flask import Blueprint, render_template, request, redirect, url_for, flash
import pandas as pd
import os
from modules.utils import role_required

expense_bp = Blueprint("expense_budget", __name__, url_prefix='/expense_budget')

# Define and ensure data folder exists
DATA_FOLDER = "data"
os.makedirs(DATA_FOLDER, exist_ok=True)
EXPENSE_FILE = os.path.join(DATA_FOLDER, "expenses.xlsx")

@expense_bp.route("/manage", methods=["GET", "POST"])
def manage_expenses():
    columns = ["Date", "Category", "Description", "Amount"]

    if os.path.exists(EXPENSE_FILE):
        df = pd.read_excel(EXPENSE_FILE)
    else:
        df = pd.DataFrame(columns=columns)

    if request.method == "POST":
        date = request.form.get("date")
        category = request.form.get("category")
        description = request.form.get("description")
        amount = request.form.get("amount")

        if not (date and category and description and amount):
            flash("All fields are required.", "warning")
        else:
            new_row = pd.DataFrame([[date, category, description, float(amount)]], columns=columns)
            df = pd.concat([df, new_row], ignore_index=True)
            df.to_excel(EXPENSE_FILE, index=False)
            flash("Expense recorded successfully.", "success")
            return redirect(url_for("expense_budget.manage_expenses"))

    total = df["Amount"].sum()

    return render_template("expense_budget/manage_expenses.html", expenses=df.to_dict(orient="records"), total=total)
