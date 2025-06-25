from flask import Blueprint, render_template, request, redirect, url_for, flash
import pandas as pd
import os
import bcrypt
from modules.utils import role_required

user_bp = Blueprint("user_mgmt", __name__, url_prefix='/user_mgmt')

USER_CREDENTIALS_FILE = "users.xlsx"

@user_bp.route("/manage_users", methods=["GET", "POST"])
@role_required(["Admin"])
def manage_users():
    columns = ["Username", "Password", "Role"]
    if os.path.exists(USER_CREDENTIALS_FILE):
        df_users = pd.read_excel(USER_CREDENTIALS_FILE)
    else:
        df_users = pd.DataFrame(columns=columns)

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        role = request.form.get("role")

        if not username or not password or not role:
            flash("All fields are required!", "warning")
        else:
            # Ensure password is hashed
            def hash_password_if_needed(pw):
                if isinstance(pw, str) and pw.startswith("$2b$"):
                    return pw  # Already hashed
                return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

            hashed_pw = hash_password_if_needed(password)

            if username in df_users["Username"].values:
                df_users.loc[df_users["Username"] == username, ["Password", "Role"]] = [hashed_pw, role]
                flash(f"✅ Updated user: {username}", "success")
            else:
                new_user = pd.DataFrame([[username, hashed_pw, role]], columns=columns)
                df_users = pd.concat([df_users, new_user], ignore_index=True)
                flash(f"✅ Added new user: {username}", "success")

            df_users.to_excel(USER_CREDENTIALS_FILE, index=False)
            return redirect(url_for("user_mgmt.manage_users"))

    users = df_users[["Username", "Role"]].to_dict(orient="records")  # Hide password from UI
    return render_template("user_mgmt/manage_users.html", users=users)

@user_bp.route("/delete_user/<username>", methods=["POST"])
@role_required(["Admin"])
def delete_user(username):
    if os.path.exists(USER_CREDENTIALS_FILE):
        df_users = pd.read_excel(USER_CREDENTIALS_FILE)
        df_users = df_users[df_users["Username"] != username]
        df_users.to_excel(USER_CREDENTIALS_FILE, index=False)
        flash(f"🗑️ Deleted user: {username}", "info")
    return redirect(url_for("user_mgmt.manage_users"))


@user_bp.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    if request.method == "POST":
        username = request.form.get("username")
        new_password = request.form.get("new_password")

        if not username or not new_password:
            flash("Both fields are required.", "warning")
            return redirect(url_for("user_mgmt.reset_password"))

        if os.path.exists(USER_CREDENTIALS_FILE):
            df = pd.read_excel(USER_CREDENTIALS_FILE)

            if username not in df["Username"].values:
                flash("Username not found.", "danger")
                return redirect(url_for("user_mgmt.reset_password"))

            import bcrypt
            hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()

            df.loc[df["Username"] == username, "Password"] = hashed
            df.to_excel(USER_CREDENTIALS_FILE, index=False)
            flash("Password reset successfully.", "success")
            return redirect(url_for("home"))

    return render_template("user_mgmt/reset_password.html")
