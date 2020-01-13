PRAGMA foreign_keys = ON;

CREATE TABLE if not exists attack_uids (
    uid VARCHAR(60) PRIMARY KEY,
    description TEXT,
    tid TEXT,
    name TEXT
    );

CREATE TABLE if not exists true_positives (
    uid VARCHAR(60),
    sentence_id integer,
    true_positive TEXT,
    element_tag TEXT,
    FOREIGN KEY(uid) REFERENCES attack_uids(uid)
    );

CREATE TABLE if not exists false_positives (
    uid VARCHAR(60),
    sentence_id integer,
    false_positive TEXT,
    FOREIGN KEY(uid) REFERENCES attack_uids(uid)
    );

CREATE TABLE if not exists false_negatives (
    uid VARCHAR(60),
    sentence_id INTEGER,
    false_negative TEXT,
    FOREIGN KEY(uid) REFERENCES attack_uids(uid)
    );

CREATE TABLE if not exists regex_patterns (
    uid integer PRIMARY KEY AUTOINCREMENT,
    attack_uid VARCHAR(60),
    regex_pattern TEXT,
    FOREIGN KEY(attack_uid) REFERENCES attack_uids(uid)
    );

CREATE TABLE if not exists similar_words (
    uid VARCHAR(60),
    attack_uid TEXT,
    similar_word TEXT,
    FOREIGN KEY(attack_uid) REFERENCES attack_uids(uid)
    );

CREATE TABLE if not exists reports (
    uid integer PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    url TEXT,
    attack_key TEXT,
    current_status TEXT
    );

CREATE TABLE if not exists report_sentences (
    uid integer PRIMARY KEY AUTOINCREMENT,
    report_uid INTEGER,
    text TEXT,
    html TEXT,
    found_status TEXT
    );

CREATE TABLE if not exists report_sentence_hits (
    uid INTEGER,
    attack_uid TEXT,
    attack_technique_name TEXT,
    report_uid INTEGER,
    attack_tid TEXT
    );

CREATE TABLE if not exists true_negatives (
    uid VARCHAR(60),
    sentence TEXT,
    FOREIGN KEY(uid) REFERENCES attack_uids(uid)
    );

CREATE TABLE if not exists original_html (
    uid INTEGER PRIMARY KEY AUTOINCREMENT,
    report_uid INTEGER,
    text TEXT,
    tag TEXT,
    found_status TEXT
    );

--INSERT INTO regex_patterns (attack_uid, regex_pattern) values ("attack-pattern--01df3350-ce05-4bdf-bdf8-0a919a66d4a8", "sometext.*moretext")
