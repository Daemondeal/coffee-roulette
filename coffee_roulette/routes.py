import os
from flask import Blueprint, flash, render_template, request, redirect, abort
from coffee_roulette.db import get_connection

bp = Blueprint("main", __name__)

def check_password(password):
    return password == os.getenv("PASSWORD", "")

# Home
@bp.route("/")
def home():
    conn = get_connection()

    # Fetch all people
    people = conn.execute("SELECT id, name FROM people ORDER BY name").fetchall()

    # Fetch extractions
    extractions = conn.execute(
        "SELECT * FROM extractions ORDER BY id DESC"
    ).fetchall()

    # Compute pickrates
    total_extractions = conn.execute("SELECT COUNT(*) FROM extractions").fetchone()[0]

    person_stats = []
    for p in people:
        count = conn.execute("""
            SELECT COUNT(*)
            FROM extraction_participants
            WHERE person_id = ?
        """, (p["id"],)).fetchone()[0]

        wins = conn.execute("""
            SELECT COUNT(*)
            FROM extractions
            WHERE result = ?
        """, (p["id"],)).fetchone()[0]

        pickrate = (wins / count * 100) if count > 0 else 0

        person_stats.append({
            "name": p["name"],
            "count": count,
            "pickrate": round(pickrate, 1)
        })

    # Build extraction list with participants
    extraction_data = []
    for ext in extractions:
        participants = conn.execute("""
            SELECT people.name
            FROM people
            JOIN extraction_participants ep ON ep.person_id = people.id
            WHERE ep.extraction_id = ?
        """, (ext["id"],)).fetchall()

        winner = conn.execute("""
            SELECT people.name
            FROM people
            WHERE people.id = ?
        """, (ext["result"],)).fetchone()

        extraction_data.append({
            "id": ext["id"],
            "result": ext["result"],
            "timestamp": ext["timestamp"],
            "participants": [p["name"] for p in participants],
            "winner": winner,
        })

    conn.close()

    return render_template(
        "index.html",
        people=person_stats,
        extractions=extraction_data
    )

# Add person
@bp.route("/people/add", methods=["GET", "POST"])
def add_person():
    if request.method == "POST":
        name = request.form["name"]
        password = request.form.get("password")

        if not check_password(password):
            flash("Invalid Password", "danger")
            return redirect("/")

        conn = get_connection()
        conn.execute("INSERT INTO people (name) VALUES (?)", (name,))
        conn.commit()
        conn.close()
        return redirect("/")
    return render_template("add_person.html")

@bp.route("/extractions/add", methods=["GET", "POST"])
def add_extraction():
    conn = get_connection()
    if request.method == "POST":
        selected_person_id = request.form.get("result")  # radio button selection
        participants = request.form.getlist("participants")  # checkboxes
        password = request.form.get("password")
        if not check_password(password):
            flash("Invalid Password", "danger")
            return redirect("/")

        cur = conn.cursor()
        cur.execute("INSERT INTO extractions (result) VALUES (?)", (selected_person_id,))
        extraction_id = cur.lastrowid

        for p in participants:
            cur.execute(
                "INSERT INTO extraction_participants (extraction_id, person_id) VALUES (?, ?)",
                (extraction_id, p)
            )

        conn.commit()
        conn.close()
        return redirect("/")

    # GET → show form
    people = conn.execute("SELECT id, name FROM people").fetchall()
    conn.close()

    return render_template("add_extraction.html", people=people)

@bp.route("/extractions/delete/<int:extraction_id>", methods=["POST"])
def delete_extraction(extraction_id):
    conn = get_connection()

    # delete participants first (FK clean-up)
    conn.execute("DELETE FROM extraction_participants WHERE extraction_id = ?", (extraction_id,))
    conn.execute("DELETE FROM extractions WHERE id = ?", (extraction_id,))

    conn.commit()
    conn.close()
    return redirect("/")
