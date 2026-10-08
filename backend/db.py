import sqlite3
import json
import os
import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "proposal_app.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        customer TEXT,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS contributions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        contributor_name TEXT,
        contributor_role TEXT,
        discipline TEXT,
        input_type TEXT,
        source_name TEXT,
        content TEXT,
        structured_fields TEXT,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS proposals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        version INTEGER NOT NULL,
        content_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)
    conn.commit()
    conn.close()


def now():
    return datetime.datetime.utcnow().isoformat()


def create_project(name, customer):
    conn = get_conn()
    cur = conn.execute("INSERT INTO projects (name, customer, created_at) VALUES (?, ?, ?)", (name, customer, now()))
    conn.commit()
    pid = cur.lastrowid
    conn.close()
    return pid


def list_projects():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_project(project_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def add_contribution(project_id, contributor_name, contributor_role, discipline, input_type, source_name, content, structured_fields):
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO contributions
           (project_id, contributor_name, contributor_role, discipline, input_type, source_name, content, structured_fields, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (project_id, contributor_name, contributor_role, discipline, input_type, source_name, content,
         json.dumps(structured_fields or {}), now()),
    )
    conn.commit()
    cid = cur.lastrowid
    conn.close()
    return cid


def list_contributions(project_id):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM contributions WHERE project_id = ? ORDER BY created_at ASC", (project_id,)).fetchall()
    conn.close()
    out = []
    for r in rows:
        d = dict(r)
        d["structured_fields"] = json.loads(d["structured_fields"] or "{}")
        out.append(d)
    return out


def save_proposal(project_id, content_dict):
    conn = get_conn()
    row = conn.execute("SELECT MAX(version) as v FROM proposals WHERE project_id = ?", (project_id,)).fetchone()
    version = (row["v"] or 0) + 1
    conn.execute(
        "INSERT INTO proposals (project_id, version, content_json, created_at) VALUES (?, ?, ?, ?)",
        (project_id, version, json.dumps(content_dict), now()),
    )
    conn.commit()
    conn.close()
    return version


def list_proposals(project_id):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM proposals WHERE project_id = ? ORDER BY version DESC", (project_id,)).fetchall()
    conn.close()
    out = []
    for r in rows:
        d = dict(r)
        d["content"] = json.loads(d.pop("content_json"))
        out.append(d)
    return out


def get_proposal(project_id, version):
    conn = get_conn()
    row = conn.execute("SELECT * FROM proposals WHERE project_id = ? AND version = ?", (project_id, version)).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d["content"] = json.loads(d.pop("content_json"))
    return d
