"""Minimal Flask + SQLite app for the DevSecOps pipeline demo.

Remediated variant: the intentional vulnerabilities documented in SEEDED_VULNS.md
have been fixed on this branch so the pipeline passes all gates.
"""

import os
import sqlite3

from flask import (
    Flask,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from markupsafe import escape

DATABASE = os.environ.get("DATABASE", "app.db")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    conn = sqlite3.connect(DATABASE)
    with open("schema.sql", "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()


@app.route("/")
def index():
    if session.get("username"):
        return redirect(url_for("items"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        db = get_db()
        # Parameterized query — the driver escapes input, preventing SQL injection.
        user = db.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, password),
        ).fetchone()
        if user:
            session["username"] = user["username"]
            return redirect(url_for("items"))
        error = "Invalid credentials"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/search")
def search():
    # Escape user input before embedding it in HTML — prevents reflected XSS.
    q = escape(request.args.get("q", ""))
    return f"<html><body><h1>Search results for: {q}</h1></body></html>"


@app.route("/items")
def items():
    if not session.get("username"):
        return redirect(url_for("login"))
    db = get_db()
    # Scope items to the logged-in user — fixes the broken-access-control flaw.
    rows = db.execute(
        "SELECT id, name, owner FROM items WHERE owner = ?",
        (session["username"],),
    ).fetchall()
    return render_template("items.html", items=rows, username=session["username"])


if __name__ == "__main__":
    if not os.path.exists(DATABASE):
        init_db()
    app.run(host="127.0.0.1", port=5000)
