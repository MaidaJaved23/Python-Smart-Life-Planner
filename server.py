"""Web API for Smart Life Planner. It wraps YOUR existing backend classes (via main.SmartLifePlanner),
adds sign up / login, and serves the frontend/ folder.   Run:  python server.py   then open http://127.0.0.1:5000"""
import dataclasses
import json
import os
import re
import secrets
import sys
from datetime import date
from functools import wraps

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from flask import Flask, jsonify, request, send_from_directory, session
from werkzeug.security import check_password_hash, generate_password_hash

from main import SmartLifePlanner

core = SmartLifePlanner()                 # your DataManager, TripPlanner, MonthlyBudgetManager, PDFReportGenerator
planner, budgets, pdf, store = core.trip_planner, core.budget_manager, core.pdf_generator, core.data_manager
USERS = os.path.join(BASE, "data", "users.json")
drafts, pending, alts = {}, {}, {}        # in-progress trips, proposed changes, calculated alternatives


def plain(o):
    """Turn model objects (dataclass / to_dict / plain object / namedtuple) into JSON-safe data."""
    if o is None or isinstance(o, (str, int, float, bool)):
        return o
    if isinstance(o, dict):
        return {str(k): plain(v) for k, v in o.items()}
    if hasattr(o, "_asdict"):
        return plain(o._asdict())
    if isinstance(o, (list, tuple, set)):
        return [plain(v) for v in o]
    if hasattr(o, "to_dict"):
        return plain(o.to_dict())
    if dataclasses.is_dataclass(o):
        return plain(dataclasses.asdict(o))
    if hasattr(o, "__dict__"):
        return {k: plain(v) for k, v in vars(o).items() if not k.startswith("_")}
    return str(o)


def read_users():
    try:
        with open(USERS, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def secret_key():
    path = os.path.join(BASE, "data", ".secret")
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(secrets.token_hex(32))
    with open(path) as f:
        return f.read().strip()


app = Flask(__name__, static_folder=os.path.join(BASE, "frontend"), static_url_path="")
app.secret_key = secret_key()
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")


@app.errorhandler(Exception)
def fail(error):
    if isinstance(error, KeyError):
        return jsonify(error=f"Missing field {error}"), 400
    code = getattr(error, "code", 400)
    return jsonify(error=str(getattr(error, "description", error))), code if isinstance(code, int) else 400


def login_required(fn):
    @wraps(fn)
    def inner(*a, **k):
        if "user" not in session:
            return jsonify(error="Please log in."), 401
        return fn(*a, **k)
    return inner


def body():
    return request.get_json(silent=True) or {}


def find_budget(budget_id):
    for b in budgets.list_budgets():
        if b.budget_id == budget_id:
            return b
    raise ValueError("Budget not found.")


def budget_view(b):
    return {"budget": plain(b), "summary": plain(budgets.calculate_financial_summary(b.budget_id))}


def find_trip(trip_id):
    trip = drafts.get(trip_id) or next((t for t in planner.confirmed_trips if t.trip_id == trip_id), None)
    if trip is None:
        raise ValueError("Trip not found. Plan it again.")
    return trip


def pdf_name(path):
    return os.path.basename(str(path))


# ---------------- auth ----------------
@app.post("/api/signup")
def signup():
    d = body()
    name, email, pw = str(d.get("name", "")).strip(), str(d.get("email", "")).strip().lower(), str(d.get("password", ""))
    if len(name) < 2:
        raise ValueError("Enter your full name.")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise ValueError("Enter a valid email address.")
    if len(pw) < 8:
        raise ValueError("Password must be at least 8 characters.")
    users = read_users()
    if any(u["email"] == email for u in users):
        raise ValueError("An account with this email already exists.")
    users.append({"name": name, "email": email, "hash": generate_password_hash(pw)})
    store_users(users)
    session["user"] = {"name": name, "email": email}
    return jsonify(session["user"])


def store_users(users):
    os.makedirs(os.path.dirname(USERS), exist_ok=True)
    with open(USERS, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)


@app.post("/api/login")
def login():
    d = body()
    email = str(d.get("email", "")).strip().lower()
    user = next((u for u in read_users() if u["email"] == email), None)
    if not user or not check_password_hash(user["hash"], str(d.get("password", ""))):
        return jsonify(error="Email or password is incorrect."), 401
    session["user"] = {"name": user["name"], "email": email}
    return jsonify(session["user"])


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify(ok=True)


@app.get("/api/me")
def me():
    return jsonify(session.get("user")) if "user" in session else (jsonify(error="Not logged in."), 401)


@app.get("/")
def home():
    return app.send_static_file("index.html")


# ---------------- trips ----------------
@app.get("/api/destinations")
@login_required
def destinations():
    with open(os.path.join(BASE, "data", "destinations.json"), encoding="utf-8") as f:
        return jsonify(json.load(f))


@app.post("/api/trips/plan")
@login_required
def plan_trip():
    d = body()
    if d.get("travel_date"):
        try:
            when = date.fromisoformat(str(d["travel_date"]))
        except ValueError:
            raise ValueError("Enter the departure date as YYYY-MM-DD.")
        if when < date.today():
            raise ValueError("Choose a departure date from today onward.")
    trip, breakdown, status, message = planner.create_trip_plan(
        budget=float(d["budget"]), travellers=int(d["travellers"]), destination_name_or_id=d["destination"],
        departure_city=str(d.get("departure_city") or "Islamabad").strip(), days=int(d["days"]), nights=int(d["nights"]),
        travel_category=d.get("travel_category", "Standard"), destination_type_pref=d.get("destination_type_pref", "Any"))
    return jsonify(trip_response(trip, status, message))


def trip_response(trip, status, message):
    drafts[trip.trip_id] = trip
    out = {"trip": plain(trip), "status": status, "message": message, "alternatives": [], "shortage": ""}
    if "over" in str(status).lower():
        try:
            from services.feasibility_checker import TripFeasibilityChecker
            out["shortage"] = TripFeasibilityChecker.explain_shortage(trip.budget, trip.cost_breakdown)
        except Exception:
            pass
        found = planner.get_trip_alternatives(trip)
        alts[trip.trip_id] = found
        out["alternatives"] = [plain(a) for a in found]
    return out


@app.post("/api/trips/<trip_id>/adopt/<int:rank>")
@login_required
def adopt(trip_id, rank):
    found = alts.get(trip_id, [])
    if not 1 <= rank <= len(found):
        raise ValueError("That alternative is no longer available.")
    chosen = found[rank - 1].modified_trip
    return jsonify(trip_response(chosen, getattr(chosen, "status", ""), ""))


@app.post("/api/trips/<trip_id>/modify")
@login_required
def modify(trip_id):
    allowed = {"budget": float, "travellers": int, "destination": str, "days": int, "nights": int, "travel_category": str}
    updates = {k: allowed[k](v) for k, v in body().items() if k in allowed and v not in ("", None)}
    if not updates:
        raise ValueError("Nothing was changed.")
    base = find_trip(trip_id)
    cand, _, status, message = planner.modify_trip_parameters(base, **updates)
    pending[trip_id] = cand
    return jsonify({"current": plain(base), "candidate": plain(cand), "status": status, "message": message})


@app.post("/api/trips/<trip_id>/accept")
@login_required
def accept(trip_id):
    cand = pending.pop(trip_id, None)
    if cand is None:
        raise ValueError("There is no proposed change to accept.")
    return jsonify(trip_response(cand, getattr(cand, "status", ""), ""))


@app.post("/api/trips/<trip_id>/cancel")
@login_required
def cancel(trip_id):
    pending.pop(trip_id, None)
    return jsonify(ok=True)


@app.post("/api/trips/<trip_id>/confirm")
@login_required
def confirm(trip_id):
    trip = find_trip(trip_id)
    already_saved = any(t.trip_id == trip_id for t in planner.confirmed_trips)
    if not already_saved and not planner.confirm_and_save_trip(trip):   # never save the same trip twice
        raise ValueError("The trip could not be saved.")
    try:
        return jsonify(file=pdf_name(pdf.generate_trip_pdf(trip)), trip=plain(trip))
    except Exception as error:                                          # the trip stays saved even if the PDF fails
        return jsonify(file=None, trip=plain(trip), pdf_error=str(error))


@app.get("/api/trips")
@login_required
def trips():
    return jsonify([plain(t) for t in planner.confirmed_trips])


@app.post("/api/trips/<trip_id>/pdf")
@login_required
def trip_pdf(trip_id):
    trip = next((t for t in planner.confirmed_trips if t.trip_id == trip_id), None)
    if trip is None:
        raise ValueError("Confirm the trip before creating its PDF.")
    return jsonify(file=pdf_name(pdf.generate_trip_pdf(trip)))


# ---------------- budgets ----------------
@app.get("/api/budgets")
@login_required
def list_budgets():
    return jsonify([budget_view(b) for b in budgets.list_budgets()])


@app.post("/api/budgets")
@login_required
def create_budget():
    d = body()
    b = budgets.create_budget(month=str(d["month"]).strip(), budget_type=d.get("budget_type", "Home & Kitchen"),
                              total_available=float(d["total_available"]))
    for name, amount in (d.get("planned") or {}).items():
        if amount not in ("", None):
            b.update_category(name, float(amount))
    budgets.save_budgets()
    return jsonify(budget_view(b))


@app.get("/api/budgets/<budget_id>")
@login_required
def get_budget(budget_id):
    return jsonify(budget_view(find_budget(budget_id)))


def saved(budget_id):
    budgets.save_budgets()
    return jsonify(budget_view(find_budget(budget_id)))


@app.post("/api/budgets/<budget_id>/categories")
@login_required
def add_category(budget_id):
    d = body()
    budgets.add_category(budget_id, str(d["name"]).strip(), float(d.get("planned") or 0))
    return saved(budget_id)


@app.put("/api/budgets/<budget_id>/categories/<path:name>")
@login_required
def set_planned(budget_id, name):
    budgets.update_category_planned(budget_id, name, float(body()["planned"]))
    return saved(budget_id)


@app.delete("/api/budgets/<budget_id>/categories/<path:name>")
@login_required
def remove_category(budget_id, name):
    budgets.remove_category(budget_id, name)
    return saved(budget_id)


@app.post("/api/budgets/<budget_id>/expenses")
@login_required
def add_expense(budget_id):
    d = body()
    if str(d["category"]).strip() not in find_budget(budget_id).planned_categories:
        budgets.add_category(budget_id, str(d["category"]).strip(), 0.0)
    budgets.record_expense(budget_id=budget_id, category=str(d["category"]).strip(), description=str(d.get("description", "")).strip(),
                           amount=float(d["amount"]), date=str(d.get("date") or date.today().isoformat()))
    return saved(budget_id)


@app.put("/api/budgets/<budget_id>/expenses/<expense_id>")
@login_required
def edit_expense(budget_id, expense_id):
    d = body()
    budgets.update_expense(budget_id=budget_id, expense_id=expense_id, category=d.get("category") or None,
                           description=d.get("description") or None,
                           amount=float(d["amount"]) if d.get("amount") not in ("", None) else None, date=d.get("date") or None)
    return saved(budget_id)


@app.delete("/api/budgets/<budget_id>/expenses/<expense_id>")
@login_required
def delete_expense(budget_id, expense_id):
    budgets.delete_expense(budget_id, expense_id)
    return saved(budget_id)


@app.post("/api/budgets/<budget_id>/pdf")
@login_required
def budget_pdf(budget_id):
    find_budget(budget_id)
    return jsonify(file=pdf_name(pdf.generate_budget_pdf(budgets.calculate_financial_summary(budget_id))))


# ---------------- reports and developer ----------------
@app.get("/api/reports")
@login_required
def reports():
    folder = store.reports_dir
    files = [f for f in os.listdir(folder) if f.lower().endswith(".pdf")] if os.path.isdir(folder) else []
    info = [{"name": f, "kb": round(os.path.getsize(os.path.join(folder, f)) / 1024, 1),
             "time": os.path.getmtime(os.path.join(folder, f))} for f in files]
    return jsonify(sorted(info, key=lambda r: -r["time"]))


@app.get("/api/reports/<path:name>")
@login_required
def report_file(name):
    return send_from_directory(store.reports_dir, name, as_attachment=True)


@app.get("/api/developer")
@login_required
def get_developer():
    return jsonify(store.load_developer_config())


@app.put("/api/developer")
@login_required
def put_developer():
    d, cur = body(), store.load_developer_config()
    email = str(d.get("email") or cur.get("email") or "").strip()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise ValueError("Email address is not valid.")
    new = {"developer_name": str(d.get("developer_name") or cur.get("developer_name") or "").strip(),
           "github_username": str(d.get("github_username") or cur.get("github_username") or "").strip(), "email": email}
    store.save_developer_config(new)
    return jsonify(new)


if __name__ == "__main__":
    app.run(debug=False, port=int(os.environ.get("PORT", 5000)))   # set PORT=5001 if 5000 is busy (macOS AirPlay)
