import os
import requests
import urllib.parse
from models import User


from flask import redirect, render_template, request, session
from functools import wraps


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def blogger_required(f):
    """Only allow users with authors to blog"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get("user_id")
        user = User.query.get(user_id) if user_id else None

        if user is None:
            return redirect("/login")

        if not user.has_role("author"):
            return redirect("/blog")   

        return f(*args, **kwargs)
    return decorated_function


def moderator_required(f):
    """Only allow admins and superadmins to moderate"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get("user_id")
        user = User.query.get(user_id) if user_id else None

        if user is None:
            return redirect("/home")   

        if not (user.has_role("admin") or user.has_role("superadmin") or user.has_role("author")):
            return redirect("/home") 

        return f(*args, **kwargs)
    return decorated_function






