import os
import datetime

from flask import Blueprint, flash, render_template, request, redirect
from coffee_roulette import utils
from coffee_roulette.db import get_connection
from coffee_roulette.model import get_all_extractions, get_all_people

bp = Blueprint("main", __name__)


def check_password(password: str) -> bool:
    return password == os.getenv("PASSWORD", "")


def get_coffe_price_cents(when: datetime.datetime) -> int:
    # TODO: Check this
    if when >= datetime.datetime(2026, 2, 26):
        return 65
    else:
        return 60


# Home
@bp.route("/")
def home():
    conn = get_connection()

    people = get_all_people(conn)
    extractions = get_all_extractions(conn, people)

    total_spent_on_coffee = 0
    for extraction in extractions:
        coffee_price = get_coffe_price_cents(extraction.date)
        total_spent_on_coffee += len(extraction.participants) * coffee_price

    people_stats = []
    for id in people:
        person = people[id]

        free_coffees = 0
        coffees_paid_to_others = 0
        net_balance = 0
        losses = 0

        for extraction in extractions:
            if id not in extraction.participants_id:
                continue

            was_extracted = extraction.extracted.id == id

            if was_extracted:
                coffees_paid_to_others += len(extraction.participants) - 1
                net_balance += get_coffe_price_cents(extraction.date) * (
                    len(extraction.participants) - 1
                )
                losses += 1
            else:
                free_coffees += 1
                net_balance -= get_coffe_price_cents(extraction.date)

        people_stats.append(
            {
                "name": person.name,
                "net_balance": net_balance,
                "coffees_paid_to_others": coffees_paid_to_others,
                "losses": losses,
                "free_coffees": free_coffees,
            }
        )

    extraction_stats = []
    for extraction in extractions:
        extraction_stats.append(
            {
                "id": extraction.id,
                "participants": [p.name for p in extraction.participants],
                "date": extraction.date,
                "extracted": extraction.extracted,
                "amount_paid_cents": len(extraction.participants)
                * get_coffe_price_cents(extraction.date),
            }
        )

    people_stats.sort(key=lambda x: x["net_balance"], reverse=True)
    extraction_stats.sort(key=lambda ex: ex["date"], reverse=True)

    conn.close()

    return render_template(
        "index.html",
        total_spent_on_coffee=total_spent_on_coffee,
        people=people_stats,
        extractions=extraction_stats,
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
        res = conn.execute("INSERT INTO people (name) VALUES (?)", (name.strip(),))
        conn.commit()
        conn.close()
        return redirect("/")
    return render_template("add_person.html")


@bp.route("/people/delete", methods=["GET", "POST"])
def delete_person():
    if request.method == "POST":
        person_id = request.form["person_id"]
        password = request.form.get("password")

        if not check_password(password):
            flash("Invalid Password", "danger")
            return redirect("/people/delete")

        conn = get_connection()

        participation_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM extraction_participants
            WHERE person_id = ?
            """,
            (person_id,),
        ).fetchone()[0]

        if participation_count > 0:
            conn.close()
            flash(
                "Cannot delete person: they participated in at least one extraction.",
                "warning",
            )
            return redirect("/people/delete")

        conn.execute("DELETE FROM people WHERE id = ?", (person_id,))
        conn.commit()
        conn.close()
        return redirect("/")

    conn = get_connection()
    people = conn.execute("SELECT id, name FROM people").fetchall()
    conn.close()

    return render_template("delete_person.html", people=people)


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

        assert selected_person_id

        cur = conn.cursor()
        cur.execute(
            "INSERT INTO extractions (result) VALUES (?)", (selected_person_id,)
        )
        extraction_id = cur.lastrowid

        participant_names = []
        for p in participants:
            participant = conn.execute(
                "SELECT name FROM people WHERE id = ?",
                (p,),
            ).fetchone()
            participant_names.append(participant["name"])

        extracted = conn.execute(
            "SELECT name FROM people WHERE id = ?",
            (selected_person_id,),
        ).fetchone()
        extracted_name = extracted["name"]

        for p in participants:
            cur.execute(
                "INSERT INTO extraction_participants (extraction_id, person_id) VALUES (?, ?)",
                (extraction_id, p),
            )

        people = get_all_people(conn)
        extractions = get_all_extractions(conn, people)
        extracted_net_spend = 0
        for extraction in extractions:
            if int(selected_person_id) not in extraction.participants_id:
                continue

            if extraction.extracted.id == int(selected_person_id):
                extracted_net_spend += get_coffe_price_cents(extraction.date) * (
                    len(extraction.participants) - 1
                )
            else:
                extracted_net_spend -= get_coffe_price_cents(extraction.date)

        conn.commit()

        message = ":loud-siren: NEW COFFEE EXTRACTION :loud-siren:\n"
        message += f"{extracted_name} just paid for this many coffees: "
        for _ in range(len(participant_names)):
            message += ":coffee: "
        message += f"\nTheir new net balance is now: {extracted_net_spend/100:.2f} €"

        utils.send_slack_message(message)

        conn.close()
        return redirect("/")

    # GET → show form
    people = conn.execute("SELECT id, name FROM people").fetchall()
    conn.close()

    return render_template("add_extraction.html", people=people)


@bp.route("/extractions/delete/<int:extraction_id>", methods=["POST"])
def delete_extraction(extraction_id):
    password = request.form.get("password")
    if not check_password(password):
        flash("Invalid Password", "danger")
        return redirect("/")

    conn = get_connection()

    # delete participants first (FK clean-up)
    conn.execute(
        "DELETE FROM extraction_participants WHERE extraction_id = ?", (extraction_id,)
    )
    conn.execute("DELETE FROM extractions WHERE id = ?", (extraction_id,))

    conn.commit()
    conn.close()
    return redirect("/")
