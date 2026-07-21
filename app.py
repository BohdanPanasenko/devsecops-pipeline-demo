"""Minimal Flask + SQLite app for the DevSecOps pipeline demo.

The app is intentionally small: it exists as a vehicle for the CI/CD security
scanning work. Step 1 keeps the code clean (parameterized queries, secret from
env); intentional vulnerabilities are seeded later in their own commits and
documented in SEEDED_VULNS.md.
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
# SEEDED VULN #2. FAKE credential, seeded for the Gitleaks demo, not real
AWS_ACCESS_KEY_ID = "AKIAVJOYIFFIVGLCNSSW"

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
        # SEEDED VULN #1 (SQL injection): user input is concatenated directly
        # into the SQL string instead of using parameters. See SEEDED_VULNS.md.
        query = (
            "SELECT * FROM users WHERE username = '%s' AND password = '%s'"
            % (username, password)
        )
        user = db.execute(query).fetchone()
        if user:
            session["username"] = user["username"]
            return redirect(url_for("items"))
        error = "Invalid credentials"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/items")
def items():
    if not session.get("username"):
        return redirect(url_for("login"))
    db = get_db()
    # SEEDED VULN #5 (broken access control): every logged-in user sees ALL
    # items regardless of the `owner` column — there is no check tying items to
    # the current user. This is a business-logic flaw NO scanner in the pipeline
    # catches. See SEEDED_VULNS.md. (Correct behavior would filter by owner.)
    rows = db.execute("SELECT id, name, owner FROM items").fetchall()
    return render_template("items.html", items=rows, username=session["username"])


if __name__ == "__main__":
    if not os.path.exists(DATABASE):
        init_db()
    app.run(host="127.0.0.1", port=5000, debug=True)
