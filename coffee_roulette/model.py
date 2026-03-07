from dataclasses import dataclass

import datetime
import sqlite3

@dataclass
class Person:
    name: str
    id: int


@dataclass
class Extraction:
    participants: list[Person]
    participants_id: set[int]
    extracted: Person
    date: datetime.datetime


def get_all_people(conn: sqlite3.Connection) -> dict[int, Person]:
    query = conn.execute("SELECT * FROM people")

    people = {}
    for row in query:
        id = int(row["id"])
        name = row["name"]

        people[id] = Person(
            id=id,
            name=name,
        )

    return people


def get_all_extractions(
    conn: sqlite3.Connection, people: dict[int, Person]
) -> list[Extraction]:
    query = conn.execute("""
        SELECT
            e.id AS extraction_id,
            e.result AS result_id,
            e.timestamp AS timestamp,
            ep.person_id AS participant_id
        FROM extractions e
        JOIN extraction_participants ep
            ON ep.extraction_id = e.id
        ORDER BY e.id
        """)

    extractions: dict[int, Extraction] = {}

    for row in query:
        extraction_id = int(row["extraction_id"])

        if extraction_id not in extractions:
            result_id = int(row["result_id"])
            timestamp = row["timestamp"]

            extractions[extraction_id] = Extraction(
                participants=[],
                participants_id=set(),
                extracted=people[result_id],
                date=datetime.datetime.fromisoformat(timestamp),
            )

        participant_id = int(row["participant_id"])
        extractions[extraction_id].participants.append(people[participant_id])
        extractions[extraction_id].participants_id.add(participant_id)

    return list(extractions.values())
