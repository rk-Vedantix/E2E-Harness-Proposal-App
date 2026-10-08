# E2E Harness — Proposal Drafting Prototype

A working prototype of the "AI-Assisted Proposal Generation" product described in the E2E Harness
project: a customer requirement comes in through multiple contributors and input types, and the
app produces a structured first-draft proposal (scope, standards, work packages, effort by
discipline, risks, and open clarification questions) that an engineer then reviews.

**This prototype uses scripted, rule-based logic, not a live LLM call.** It keyword-matches the
combined text from every contribution against a small library of domain templates (harness LV,
harness HV/EV, DC-DC/PDU, electrical architecture, defence/MIL-spec, plus a generic fallback), the
same way the earlier draft proposals you reviewed were structured. It's built so the matching step
is the one seam to swap for a real model call later — see "Wiring in a real LLM" below.

## What it demonstrates

- **Multiple contributors, one project.** The business-development manager who met the customer
  can log meeting notes; the engineers and project managers who actually scope the work can add a
  structured form, a pasted customer email, or an uploaded reference document — all against the
  same project, each attributed by name, role and discipline.
- **Four input types**: a structured form (project type, volume, regions, notes), document upload
  (.pdf / .docx / .txt — text is extracted automatically), pasted free text (e.g. an email thread),
  and typed meeting/verbal notes.
- **Draft generation**: combines every contribution's text, scores it against the domain library,
  merges work packages (with a light "hybrid scope" handling when two domains both score highly),
  adds a functional-safety or homologation work package when that language is detected, scales
  manufacturing effort for low-volume/prototype vs. high-volume language, and flags anything a
  domain's checklist expected but didn't find (e.g. "What is the continuous / peak current
  rating?") as an open clarification question.
- **Version history** — regenerating after adding more contributions creates a new version; old
  versions stay visible.
- **Word export** — any version downloads as a formatted .docx (landscape, so the 9-discipline
  effort table stays readable), in the same structure as the manually-drafted proposals.

## Running it

Requires Python 3.10+.

```bash
cd backend
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 8000
```

Then open **http://127.0.0.1:8000/** in a browser. The backend serves the frontend directly, so
there's nothing separate to build or run — one process, one port.

Data is stored in `backend/proposal_app.db` (SQLite, created automatically on first run). Delete
that file to reset to an empty app.

## Project layout

```
backend/
  app.py            FastAPI routes (projects, contributions, generate, docx download)
  db.py             SQLite schema and access (projects / contributions / proposals)
  knowledge_base.py  The domain library: keywords, standards, work packages + effort hours,
                     missing-info checks, cross-domain add-on signals (functional safety etc.)
  engine.py         Turns a project's contributions into a scored, structured draft
  extract.py        Text extraction from uploaded .pdf / .docx / .txt files
  docx_export.py    Renders a generated draft to a formatted .docx
frontend/
  index.html, app.js, style.css   Plain HTML/JS single-page app, no build step
```

## Extending it

- **More domains**: add an entry to `DOMAINS` in `knowledge_base.py` (keywords, standards, work
  packages with 9-discipline hour arrays, a contingency %, missing-info checks, risks). The engine
  and both UIs (web + docx) pick it up automatically — nothing else to change. The proposals you
  already reviewed (marine, rail, aerospace, regional homologation, bus integration, smart-PCB PDU,
  off-highway) aren't in this prototype's knowledge base yet; the five domains here (LV harness, HV
  harness, DC-DC/PDU, architecture/schematic, defence) are enough to prove the pattern.
- **Wiring in a real LLM**: `engine.generate()` is the seam. Today it does keyword scoring and
  template merging; a real version would send the combined contribution text (and any uploaded
  document text) to a model with the domain library as grounding context, and ask it to select/
  blend domains, draft the missing-info questions, and adjust the work packages — while keeping the
  effort *hours* and *standards* coming from the verified library rather than the model, per the
  project's own "AI proposes, engineering data verifies, rules govern, humans approve" principle.
- **Audio input**: the "Meeting / verbal notes" tab currently takes typed notes. Swapping in actual
  speech-to-text (e.g. so a BD manager can talk instead of type after a customer call) would plug
  into the same `input_type=notes` contribution endpoint — only the frontend tab needs a recorder
  and a transcription call before submitting.
- **Auth / real multi-user**: there's no login — anyone using the app types their own name per
  contribution. Fine for a prototype; a real deployment would want actual accounts so contributions
  can't be misattributed.

## Known limitations (prototype, not production)

- No authentication — anyone with the URL can create projects and add contributions.
- SQLite, single file — fine for a demo, not for concurrent multi-user production load.
- The keyword-matching engine is intentionally simple; it will occasionally pick the wrong domain
  or miss a clarification question a human wouldn't. That's expected for a scripted demo and is the
  reason every draft carries "Approval status: DRAFT — requires review" on both the web view and
  the exported document.
- No effort/rate-card calibration — hours are the same engineering-judgement estimates used in the
  earlier manually-drafted proposals, not tied to any actual rate card or historical project data.
