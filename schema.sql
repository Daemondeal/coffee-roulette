CREATE TABLE IF NOT EXISTS people (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS extractions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    result INTEGER NOT NULL,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (result) REFERENCES people(id)
);

CREATE TABLE IF NOT EXISTS extraction_participants (
    extraction_id INTEGER NOT NULL,
    person_id INTEGER NOT NULL,
    FOREIGN KEY (extraction_id) REFERENCES extractions(id),
    FOREIGN KEY (person_id) REFERENCES people(id)
);
