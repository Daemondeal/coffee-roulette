import datetime
import os

from flask import current_app

from coffee_roulette.model import Extraction, Person
import numpy as np
import time


def calculate_percentiles(person: Person, extractions: list[Extraction]) -> list[float]:
    start = time.perf_counter()

    effort = int(os.getenv("PERCENTILE_EFFORT", "100000"))
    extractions = [e for e in extractions if person.id in e.participants_id]

    counts = np.array([len(e.participants_id) for e in extractions])
    prices = np.array([get_coffe_price_cents(e.date) for e in extractions])
    coffees_drank = np.sum(prices)

    n = len(counts)
    if n == 0:
        return []

    draws = np.random.uniform(0.0, 1.0, size=(effort, n))
    losses = np.floor(draws * counts) == 0

    weighted = prices * counts
    results = (losses @ weighted - coffees_drank) / 100

    results.sort()

    elapsed = time.perf_counter() - start
    current_app.logger.info(
        f"calculate_percentiles: effort={effort} extractions={n} took {elapsed*1000:.4f} ms"
    )

    return results.tolist()


def get_coffe_price_cents(when: datetime.datetime) -> int:
    # TODO: Check this
    if when >= datetime.datetime(2026, 2, 26):
        return 65
    else:
        return 60


def calculate_stats_for_person(person, extractions):
    id = person.id

    free_coffees = 0
    coffees_paid_to_others = 0
    net_balance = 0
    losses = 0
    participations = 0

    for extraction in extractions:
        if id not in extraction.participants_id:
            continue

        participations += 1
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

    return {
        "id": person.id,
        "name": person.name,
        "net_balance": net_balance,
        "coffees_paid_to_others": coffees_paid_to_others,
        "losses": losses,
        "free_coffees": free_coffees,
        "participations": participations,
    }


def calculate_leaderboard(people, extractions):
    return [calculate_stats_for_person(people[id], extractions) for id in people]
