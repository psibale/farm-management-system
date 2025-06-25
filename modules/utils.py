from functools import wraps
from flask import session, redirect, url_for, flash

def role_required(required_roles):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if "role" not in session or session["role"] not in required_roles:
                flash("Access denied: Insufficient privileges", "warning")
                return redirect(url_for("inventory.dashboard"))
            return f(*args, **kwargs)
        return wrapped
    return decorator


from functools import wraps
from flask import session, redirect, url_for, flash

def role_required(required_roles):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if "role" not in session or session["role"] not in required_roles:
                flash("Access denied: Insufficient privileges", "warning")
                return redirect(url_for("inventory.dashboard"))
            return f(*args, **kwargs)
        return wrapped
    return decorator
