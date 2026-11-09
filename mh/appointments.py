"""
Appointment booking.

Recommended interval follows the Indian ANC / WHO 8-contact pattern and is
shortened by the doctor-confirmed risk:
    < 28 weeks : every 4 weeks      (High risk: every 2 weeks)
    28-36 weeks: every 2 weeks      (High risk: every week)
    >= 36 weeks: every week
Moderate risk caps the interval at 3 weeks.

Clinic: Monday-Saturday, 09:00-13:00, 20-minute slots. Visits already in
the dataset for a day occupy that day's first slots. A slot can be held by
only one booking, and a patient can hold only one active booking per day.
Bookings are stored in app_data/appointments.csv.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "app_data" / "appointments.csv"
COLS = ["Booking_ID", "Created", "Pregnancy_ID", "Patient_ID", "Date", "Time", "Type", "Reason", "Status"]

OPEN, CLOSE, SLOT_MIN = time(9, 0), time(13, 0), 20
VISIT_TYPES = ["Routine ANC check-up", "Follow-up on test results", "Diet / nutrition consultation",
               "Ultrasound / scan", "Urgent concern (same day)"]

DANGER_SIGNS = [
    "Bleeding from the vagina",
    "Severe headache, blurred vision or fits",
    "Severe abdominal pain",
    "Water leaking / gush of fluid",
    "Baby moving less than usual",
    "High fever",
    "Sudden swelling of face, hands or feet",
    "Difficulty breathing",
]


def recommended_interval_days(ga_weeks: float, risk: str) -> int:
    if ga_weeks >= 36:
        return 7
    if ga_weeks >= 28:
        return 7 if risk == "High" else 14
    days = 14 if risk == "High" else 28
    if risk == "Moderate":
        days = min(days, 21)
    return days


def recommended_window(today: date, ga_weeks: float, risk: str, doctor_next: date | None = None):
    """(earliest, ideal, latest) dates for the next visit."""
    if doctor_next is not None and doctor_next >= today:
        ideal = doctor_next
    else:
        ideal = today + timedelta(days=recommended_interval_days(ga_weeks, risk))
    return ideal - timedelta(days=3), ideal, ideal + timedelta(days=3)


def all_slots() -> list[str]:
    out, t = [], datetime.combine(date.today(), OPEN)
    while t.time() < CLOSE:
        out.append(t.strftime("%H:%M"))
        t += timedelta(minutes=SLOT_MIN)
    return out


def load() -> pd.DataFrame:
    if STORE.exists():
        return pd.read_csv(STORE, keep_default_na=False, dtype=str)
    return pd.DataFrame(columns=COLS)


def _save(df: pd.DataFrame):
    STORE.parent.mkdir(exist_ok=True)
    df[COLS].to_csv(STORE, index=False)


def free_slots(day: date, dataset_visits: pd.DataFrame) -> list[str]:
    if day.weekday() == 6:      # Sunday
        return []
    slots = all_slots()
    n_existing = int((dataset_visits.Visit_Date.dt.date == day).sum())
    taken = set(slots[:n_existing])
    b = load()
    b = b[(b.Date == day.isoformat()) & (b.Status == "Booked")]
    taken |= set(b.Time)
    return [s for s in slots if s not in taken]


def book(pregnancy_id: str, patient_id: str, day: date, slot: str, vtype: str, reason: str,
         dataset_visits: pd.DataFrame) -> tuple[bool, str]:
    if day.weekday() == 6:
        return False, "The clinic is closed on Sundays."
    if slot not in free_slots(day, dataset_visits):
        return False, f"{slot} on {day:%d %b} was just taken. Please pick another slot."
    b = load()
    mine = b[(b.Pregnancy_ID == pregnancy_id) & (b.Date == day.isoformat()) & (b.Status == "Booked")]
    if len(mine):
        return False, f"You already have an appointment on {day:%d %b} at {mine.Time.iloc[0]}."
    bid = f"APT{len(b) + 1:05d}"
    row = {"Booking_ID": bid, "Created": datetime.now().strftime("%Y-%m-%d %H:%M"),
           "Pregnancy_ID": pregnancy_id, "Patient_ID": patient_id, "Date": day.isoformat(), "Time": slot,
           "Type": vtype, "Reason": reason, "Status": "Booked"}
    _save(pd.concat([b, pd.DataFrame([row])], ignore_index=True))
    return True, bid


def cancel(booking_id: str):
    b = load()
    b.loc[b.Booking_ID == booking_id, "Status"] = "Cancelled"
    _save(b)


def for_patient(pregnancy_id: str) -> pd.DataFrame:
    b = load()
    return b[b.Pregnancy_ID == pregnancy_id].sort_values(["Date", "Time"])


def for_day(day) -> pd.DataFrame:
    b = load()
    return b[(b.Date == pd.Timestamp(day).date().isoformat()) & (b.Status == "Booked")].sort_values("Time")
