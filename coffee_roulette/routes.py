import os
import datetime
from functools import wraps
from urllib.parse import urlencode

from flask import Blueprint, flash, render_template, request, redirect, send_file, session
from coffee_roulette import db, utils
from coffee_roulette.db import get_connection
from coffee_roulette.model import get_all_extractions, get_all_people
from coffee_roulette.stats import calculate_leaderboard, calculate_percentiles, calculate_stats_for_person

bp = Blueprint("main", __name__)


def check_password(password: str) -> bool:
    return password == os.getenv("PASSWORD", "")


def is_logged_in() -> bool:
    return session.get("logged_in", False)


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if is_logged_in():
            return view(*args, **kwargs)

        flash("Please log in first", "warning")
        next_url = request.full_path.rstrip("?") if request.method == "GET" else "/"
        return redirect(f"/login?{urlencode({'next': next_url})}")

    return wrapped_view


def get_coffe_price_cents(when: datetime.datetime) -> int:
    # TODO: Check this
    if when >= datetime.datetime(2026, 2, 26):
        return 65
    else:
        return 60


@bp.route("/download", methods=["GET", "POST"])
@login_required
def download_database():
    if request.method == "POST":
        database_path = db.PATH_DB.resolve()
        if not database_path.is_file():
            flash("Database not found", "warning")
            return redirect("/download")

        return send_file(
            database_path,
            as_attachment=True,
            download_name="coffee-roulette.db",
            mimetype="application/octet-stream",
        )

    return render_template("download.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    next_url = request.args.get("next") or "/"
    if not next_url.startswith("/") or next_url.startswith("//"):
        next_url = "/"

    if is_logged_in():
        return redirect(next_url)

    if request.method == "POST":
        password = request.form.get("password")
        if not check_password(password):
            flash("Invalid Password", "danger")
            return redirect(f"/login?{urlencode({'next': next_url})}")

        session.permanent = True
        session["logged_in"] = True
        flash("Logged in", "success")
        return redirect(next_url)

    return render_template("login.html", next_url=next_url)


@bp.route("/logout", methods=["POST"])
def logout():
    session.pop("logged_in", None)
    flash("Logged out", "success")
    return redirect("/")


# Home
@bp.route("/")
def home():
    conn = get_connection()

    people = get_all_people(conn)
    extractions = get_all_extractions(conn, people)
    leaderboard_options = [
        {
            "key": "net_balance",
            "label": "Money Lost",
            "stat_key": "net_balance",
        },
        {
            "key": "participations",
            "label": "Participations",
            "stat_key": "participations",
        },
        {
            "key": "paid",
            "label": "Coffees paid",
            "stat_key": "coffees_paid_to_others",
        },
        {
            "key": "free",
            "label": "Free coffees",
            "stat_key": "free_coffees",
        },
        {
            "key": "losses",
            "label": "Times lost",
            "stat_key": "losses",
        },
    ]
    selected_leaderboard = request.args.get("leaderboard", "net_balance")
    leaderboard_option = next(
        (
            option
            for option in leaderboard_options
            if option["key"] == selected_leaderboard
        ),
        leaderboard_options[0],
    )

    total_spent_on_coffee = 0
    for extraction in extractions:
        coffee_price = get_coffe_price_cents(extraction.date)
        total_spent_on_coffee += len(extraction.participants) * coffee_price

    people_stats = calculate_leaderboard(people, extractions)

    for person_stat in people_stats:
        value = person_stat[leaderboard_option["stat_key"]]
        if leaderboard_option["key"] == "net_balance":
            person_stat["leaderboard_value"] = f"{value / 100:.2f}€"
        else:
            person_stat["leaderboard_value"] = value

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

    people_stats.sort(key=lambda x: x["name"].lower())
    people_stats.sort(key=lambda x: x[leaderboard_option["stat_key"]], reverse=True)
    extraction_stats.sort(key=lambda ex: ex["date"], reverse=True)

    conn.close()

    return render_template(
        "index.html",
        total_spent_on_coffee=total_spent_on_coffee,
        people=people_stats,
        leaderboard_options=leaderboard_options,
        selected_leaderboard=leaderboard_option["key"],
        selected_leaderboard_label=leaderboard_option["label"],
        extractions=extraction_stats,
    )


@bp.route("/percentile")
def percentile():
    selected_person_id = request.args.get("person_id")

    conn = get_connection()


    selected_person = None
    selected_person_percentile = None
    selected_person_value = None
    if selected_person_id:
        people = get_all_people(conn)
        extractions = get_all_extractions(conn, people)
        selected_person = people.get(int(selected_person_id))

        if selected_person is not None:
            selected_person_percentile = calculate_percentiles(selected_person, extractions)
            selected_person_value = calculate_stats_for_person(selected_person, extractions)["net_balance"] / 100
        else:
            flash("Person not found", "warning")

    people = conn.execute("SELECT id, name FROM people ORDER BY name").fetchall()
    conn.close()

    return render_template(
        "percentile.html",
        people=people,
        selected_person=selected_person,
        selected_person_value=selected_person_value,
        selected_person_percentile=selected_person_percentile,
    )


# Add person
@bp.route("/people/add", methods=["GET", "POST"])
@login_required
def add_person():
    if request.method == "POST":
        name = request.form["name"]

        conn = get_connection()
        res = conn.execute("INSERT INTO people (name) VALUES (?)", (name.strip(),))
        conn.commit()
        conn.close()
        return redirect("/")
    return render_template("add_person.html")


@bp.route("/people/edit", methods=["GET", "POST"])
@login_required
def edit_person():
    conn = get_connection()

    if request.method == "POST":
        person_id = request.form["person_id"]
        name = request.form["name"].strip()

        if not name:
            conn.close()
            flash("Name is required", "warning")
            return redirect(f"/people/edit?person_id={person_id}")

        conn.execute("UPDATE people SET name = ? WHERE id = ?", (name, person_id))
        conn.commit()
        conn.close()

        flash("Person updated", "success")
        return redirect("/")

    selected_person_id = request.args.get("person_id")
    selected_person = None
    if selected_person_id:
        selected_person = conn.execute(
            "SELECT id, name FROM people WHERE id = ?",
            (selected_person_id,),
        ).fetchone()
        if selected_person is None:
            flash("Person not found", "warning")

    people = conn.execute("SELECT id, name FROM people ORDER BY name").fetchall()
    conn.close()

    return render_template(
        "edit_person.html",
        people=people,
        selected_person=selected_person,
    )


@bp.route("/people/delete", methods=["GET", "POST"])
@login_required
def delete_person():
    if request.method == "POST":
        person_id = request.form["person_id"]

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
@login_required
def add_extraction():
    conn = get_connection()
    if request.method == "POST":
        selected_person_id = request.form.get("result")  # radio button selection
        participants = request.form.getlist("participants")  # checkboxes

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

        message = ":pepo_coffee: NEW COFFEE EXTRACTION :meow_coffee:\n"
        message += f"{extracted_name} just paid for this many coffees: "
        for _ in range(len(participant_names)):
            message += ":coffee: "
        message += f"\nTheir new net expense is now: {extracted_net_spend/100:.2f} €"

        utils.send_slack_message(message)

        conn.close()
        return redirect("/")

    # GET -> show form
    people = conn.execute(
        """
        SELECT
            p.id,
            p.name,
            MAX(e.timestamp) AS last_participated_at,
            COUNT(ep.extraction_id) AS participation_count
        FROM people p
        LEFT JOIN extraction_participants ep
            ON ep.person_id = p.id
        LEFT JOIN extractions e
            ON e.id = ep.extraction_id
        GROUP BY p.id, p.name
        ORDER BY
            last_participated_at IS NULL,
            last_participated_at DESC,
            participation_count DESC,
            p.name COLLATE NOCASE
        """
    ).fetchall()
    conn.close()

    return render_template("add_extraction.html", people=people)


@bp.route("/extractions/delete/<int:extraction_id>", methods=["POST"])
@login_required
def delete_extraction(extraction_id):
    conn = get_connection()

    # delete participants first (FK clean-up)
    conn.execute(
        "DELETE FROM extraction_participants WHERE extraction_id = ?", (extraction_id,)
    )
    conn.execute("DELETE FROM extractions WHERE id = ?", (extraction_id,))

    conn.commit()
    conn.close()
    return redirect("/")
