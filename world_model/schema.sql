-- Schema for the CourseGen PoC world model (relational SQLite store).

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS concepts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    summary TEXT,
    parent_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES concepts(id)
);

CREATE TABLE IF NOT EXISTS relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    justification TEXT,
    FOREIGN KEY (source_id) REFERENCES concepts(id),
    FOREIGN KEY (target_id) REFERENCES concepts(id)
);

CREATE TABLE IF NOT EXISTS papers (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    venue TEXT,
    year INTEGER,
    url TEXT
);

CREATE TABLE IF NOT EXISTS authors (
    id TEXT PRIMARY KEY,
    full_name TEXT NOT NULL,
    affiliation TEXT
);

CREATE TABLE IF NOT EXISTS paper_authors (
    paper_id TEXT NOT NULL,
    author_id TEXT NOT NULL,
    position INTEGER,
    PRIMARY KEY (paper_id, author_id),
    FOREIGN KEY (paper_id) REFERENCES papers(id),
    FOREIGN KEY (author_id) REFERENCES authors(id)
);

CREATE TABLE IF NOT EXISTS claims (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id TEXT NOT NULL,
    body TEXT NOT NULL,
    citation TEXT,
    created_by TEXT,
    provenance TEXT,
    confidence REAL DEFAULT 0.5,
    asserted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (subject_id) REFERENCES concepts(id)
);

CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_year INTEGER,
    event_label TEXT NOT NULL,
    summary TEXT,
    related_concept TEXT,
    citation TEXT,
    FOREIGN KEY (related_concept) REFERENCES concepts(id)
);

CREATE TABLE IF NOT EXISTS artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_type TEXT NOT NULL,
    uri TEXT NOT NULL,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS provenance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT,
    stage TEXT,
    input_hash TEXT,
    artifact_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (artifact_id) REFERENCES artifacts(id)
);
