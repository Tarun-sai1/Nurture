"""
Nurture — Maternal Health Decision Support (web app)

Run:   python server.py
Open:  http://localhost:8000
"""
import os
import threading
import webbrowser
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from mh.service import Service

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"

print("Loading data and models (about 10 seconds)...")
svc = Service()
# Pre-computing every explanation makes clicks instant on a normal CPU. On tiny free
# hosting CPUs (e.g. Render free, 0.1 CPU) it would slow everything down, so it can
# be switched off with NURTURE_WARM=0; explanations are then computed on demand.
if os.environ.get("NURTURE_WARM", "1") != "0":
    threading.Thread(target=svc.warm_explanations, daemon=True).start()
print("Ready: open http://localhost:" + os.environ.get("PORT", "8000") + "  (press Ctrl+C to stop)")

app = FastAPI(title="Nurture API", docs_url="/api/docs")
app.add_middleware(GZipMiddleware, minimum_size=800)


def _check_preg(preg: str):
    if preg not in set(svc.data.patients.Pregnancy_ID):
        raise HTTPException(404, f"Unknown pregnancy {preg}")


# ------------------------------------------------------------------ reads
@app.get("/api/meta")
def meta():
    return svc.meta()


@app.get("/api/visits/{preg}")
def visits(preg: str):
    _check_preg(preg)
    return svc.visits(preg)


@app.get("/api/record/{preg}/{visit_id}")
def record(preg: str, visit_id: str):
    _check_preg(preg)
    if visit_id not in svc.visit_index.index:
        raise HTTPException(404, f"Unknown visit {visit_id}")
    return svc.record(preg, visit_id)


@app.get("/api/explain/{visit_id}/{target}")
def explain(visit_id: str, target: str):
    if target not in svc.models:
        raise HTTPException(404, "Unknown model")
    return svc.explain(visit_id, target)


@app.get("/api/clinic/{day}")
def clinic(day: str):
    return svc.clinic(day)


@app.get("/api/worklist")
def worklist():
    return svc.worklist()


@app.get("/api/slots/{day}")
def slots(day: str):
    return svc.slots(day)


@app.get("/api/model")
def model():
    return svc.model_report()


# ------------------------------------------------------------------ writes
class Booking(BaseModel):
    pregnancy_id: str
    day: str
    slot: str
    type: str
    reason: str = ""


class Review(BaseModel):
    pregnancy_id: str
    visit_id: str
    decisions: list[dict]
    reason: str = ""


class Note(BaseModel):
    role: str
    pregnancy_id: str
    visit_id: str
    kind: str
    text: str


class DrugCheck(BaseModel):
    pregnancy_id: str
    visit_id: str
    drug: str


@app.post("/api/appointments")
def book(b: Booking):
    _check_preg(b.pregnancy_id)
    return svc.book(b.pregnancy_id, b.day, b.slot, b.type, b.reason)


@app.post("/api/appointments/{booking_id}/cancel")
def cancel(booking_id: str):
    return svc.cancel(booking_id)


@app.post("/api/review")
def review(r: Review):
    _check_preg(r.pregnancy_id)
    return svc.save_review(r.pregnancy_id, r.visit_id, r.decisions, r.reason)


@app.post("/api/notes")
def note(n: Note):
    _check_preg(n.pregnancy_id)
    return svc.add_note(n.role, n.pregnancy_id, n.visit_id, n.kind, n.text)


@app.post("/api/drug-check")
def drug_check(d: DrugCheck):
    _check_preg(d.pregnancy_id)
    return svc.drug_check(d.pregnancy_id, d.visit_id, d.drug)


# ------------------------------------------------------------------ front end
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})


if __name__ == "__main__":
    # Locally: http://localhost:8000 and the browser opens by itself.
    # On a hosting platform (Hugging Face, Render…) PORT is set for us and we
    # listen on all interfaces instead.
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0" if "PORT" in os.environ else "127.0.0.1")
    if "PORT" not in os.environ:
        threading.Timer(1.5, lambda: webbrowser.open(f"http://localhost:{port}")).start()
    uvicorn.run(app, host=host, port=port, log_level="warning")
