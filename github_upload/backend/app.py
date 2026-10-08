import json
import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

import db
import engine
import extract
import docx_export
from knowledge_base import DOMAINS, DISCIPLINES, DISCIPLINE_FULL

db.init_db()

app = FastAPI(title="E2E Harness — Proposal Drafting Prototype")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")


@app.get("/api/meta")
def meta():
    return {
        "disciplines": DISCIPLINES,
        "discipline_full": DISCIPLINE_FULL,
        "domains": [{"key": k, "label": v["label"]} for k, v in DOMAINS.items() if k != "other"],
        "input_types": ["form", "upload", "paste", "notes"],
    }


@app.post("/api/projects")
def create_project(name: str = Form(...), customer: str = Form("")):
    pid = db.create_project(name, customer)
    return db.get_project(pid)


@app.get("/api/projects")
def get_projects():
    return db.list_projects()


@app.get("/api/projects/{project_id}")
def get_project(project_id: int):
    p = db.get_project(project_id)
    if not p:
        raise HTTPException(404, "Project not found")
    p["contributions"] = db.list_contributions(project_id)
    p["proposals"] = db.list_proposals(project_id)
    return p


@app.post("/api/projects/{project_id}/contributions")
async def add_contribution(
    project_id: int,
    contributor_name: str = Form(...),
    contributor_role: str = Form(""),
    discipline: str = Form(""),
    input_type: str = Form("paste"),
    text_content: str = Form(""),
    structured_fields: str = Form("{}"),
    file: UploadFile = File(None),
):
    if not db.get_project(project_id):
        raise HTTPException(404, "Project not found")

    content = text_content or ""
    source_name = None
    if file is not None and file.filename:
        data = await file.read()
        source_name = file.filename
        extracted = extract.extract_text(file.filename, data)
        content = (content + "\n" + extracted).strip()

    try:
        fields = json.loads(structured_fields or "{}")
    except json.JSONDecodeError:
        fields = {}

    # fold structured form fields into the searchable text too, so the engine sees them
    if fields:
        content = content + "\n" + "\n".join(f"{k}: {v}" for k, v in fields.items() if v)

    cid = db.add_contribution(project_id, contributor_name, contributor_role, discipline,
                               input_type, source_name, content.strip(), fields)
    return {"id": cid}


@app.post("/api/projects/{project_id}/generate")
def generate_proposal(project_id: int):
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    contributions = db.list_contributions(project_id)
    if not contributions:
        raise HTTPException(400, "Add at least one contribution before generating a draft.")
    result = engine.generate(contributions)
    version = db.save_proposal(project_id, result)
    return {"version": version, "content": result}


@app.get("/api/projects/{project_id}/proposals/{version}/download")
def download_proposal(project_id: int, version: int):
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    proposal = db.get_proposal(project_id, version)
    if not proposal:
        raise HTTPException(404, "Proposal version not found")
    buf = docx_export.build_docx(project, proposal["content"], version)
    filename = f"{project['name'].replace(' ', '_')}_proposal_v{version}.docx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# Serve the frontend last so /api/* routes above take priority
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
