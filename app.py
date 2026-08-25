import os
import re
from datetime import date, timedelta

from flask import (
    Flask, render_template, request, redirect, url_for, flash, jsonify,
)
from models import db, Food, DailyTarget, DiaryEntry, DailyBurn

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
database_url = os.environ.get("DATABASE_URL", "sqlite:///" + os.path.join(BASE_DIR, "food_tracking.db"))
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = os.path.join(BASE_DIR, "uploads")
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24))

db.init_app(app)

NUTRIENTS = [
    ("calories", "Kalorien", "kcal", 2000, True),
    ("fat", "Fett", "g", 65, True),
    ("saturated_fat", "Ges. Fettsäuren", "g", 20, True),
    ("carbs", "Kohlenhydrate", "g", 300, False),
    ("sugar", "Zucker", "g", 50, True),
    ("protein", "Eiweiß", "g", 50, False),
    ("fiber", "Ballaststoffe", "g", 30, False),
    ("salt", "Salz", "g", 6, True),
]

MEAL_TYPES = [
    ("breakfast", "Frühstück"),
    ("lunch", "Mittagessen"),
    ("dinner", "Abendessen"),
    ("snack", "Snack"),
]


def seed_targets():
    if DailyTarget.query.count() == 0:
        for key, label, unit, value, is_limit in NUTRIENTS:
            db.session.add(DailyTarget(
                nutrient=key, label=label, target_value=value,
                unit=unit, is_upper_limit=is_limit,
            ))
        db.session.commit()


def get_daily_summary(day):
    entries = DiaryEntry.query.filter_by(date=day).all()
    totals = {n[0]: 0.0 for n in NUTRIENTS}
    for entry in entries:
        factor = entry.amount_g / 100.0
        for key, *_ in NUTRIENTS:
            totals[key] += getattr(entry.food, key, 0) * factor
    targets = {t.nutrient: t for t in DailyTarget.query.all()}
    summary = []
    for key, label, unit, *_ in NUTRIENTS:
        t = targets.get(key)
        target_val = t.target_value if t else 0
        is_limit = t.is_upper_limit if t else False
        current = round(totals[key], 1)
        diff = round(current - target_val, 1)
        pct = round((current / target_val) * 100, 1) if target_val else 0
        summary.append({
            "key": key, "label": label, "unit": unit,
            "current": current, "target": target_val,
            "diff": diff, "pct": pct, "is_limit": is_limit,
        })
    return summary, entries


# --- Routes ---

@app.route("/")
def dashboard():
    day_str = request.args.get("date", date.today().isoformat())
    try:
        day = date.fromisoformat(day_str)
    except ValueError:
        day = date.today()
    summary, entries = get_daily_summary(day)
    prev_day = (day - timedelta(days=1)).isoformat()
    next_day = (day + timedelta(days=1)).isoformat()
    meals = {}
    for entry in entries:
        meals.setdefault(entry.meal_type, []).append(entry)
    burn = DailyBurn.query.filter_by(date=day).first()
    calories_burned = burn.calories_burned if burn else None
    return render_template(
        "dashboard.html", summary=summary, day=day, meals=meals,
        meal_types=MEAL_TYPES, prev_day=prev_day, next_day=next_day,
        today=date.today(), calories_burned=calories_burned,
    )


@app.route("/foods")
def food_list():
    q = request.args.get("q", "").strip()
    if q:
        foods = Food.query.filter(Food.name.ilike(f"%{q}%")).order_by(Food.name).all()
    else:
        foods = Food.query.order_by(Food.name).all()
    return render_template("foods.html", foods=foods, q=q)


@app.route("/foods/add", methods=["GET", "POST"])
def food_add():
    if request.method == "POST":
        food = Food(
            name=request.form["name"],
            brand=request.form.get("brand", ""),
            calories=float(request.form.get("calories") or 0),
            fat=float(request.form.get("fat") or 0),
            saturated_fat=float(request.form.get("saturated_fat") or 0),
            carbs=float(request.form.get("carbs") or 0),
            sugar=float(request.form.get("sugar") or 0),
            protein=float(request.form.get("protein") or 0),
            fiber=float(request.form.get("fiber") or 0),
            salt=float(request.form.get("salt") or 0),
            serving_size=float(request.form.get("serving_size") or 100),
        )
        db.session.add(food)
        db.session.commit()
        flash(f"'{food.name}' wurde gespeichert.", "success")
        return redirect(url_for("food_list"))
    return render_template("food_form.html", food=None)


@app.route("/foods/<int:food_id>/edit", methods=["GET", "POST"])
def food_edit(food_id):
    food = Food.query.get_or_404(food_id)
    if request.method == "POST":
        food.name = request.form["name"]
        food.brand = request.form.get("brand", "")
        food.calories = float(request.form.get("calories") or 0)
        food.fat = float(request.form.get("fat") or 0)
        food.saturated_fat = float(request.form.get("saturated_fat") or 0)
        food.carbs = float(request.form.get("carbs") or 0)
        food.sugar = float(request.form.get("sugar") or 0)
        food.protein = float(request.form.get("protein") or 0)
        food.fiber = float(request.form.get("fiber") or 0)
        food.salt = float(request.form.get("salt") or 0)
        food.serving_size = float(request.form.get("serving_size") or 100)
        db.session.commit()
        flash(f"'{food.name}' wurde aktualisiert.", "success")
        return redirect(url_for("food_list"))
    return render_template("food_form.html", food=food)


@app.route("/foods/<int:food_id>/delete", methods=["POST"])
def food_delete(food_id):
    food = Food.query.get_or_404(food_id)
    DiaryEntry.query.filter_by(food_id=food.id).delete()
    db.session.delete(food)
    db.session.commit()
    flash(f"'{food.name}' wurde gelöscht.", "success")
    return redirect(url_for("food_list"))


@app.route("/diary/add", methods=["POST"])
def diary_add():
    day_str = request.form.get("date", date.today().isoformat())
    entry = DiaryEntry(
        date=date.fromisoformat(day_str),
        meal_type=request.form.get("meal_type", "snack"),
        food_id=int(request.form["food_id"]),
        amount_g=float(request.form.get("amount_g") or 100),
    )
    db.session.add(entry)
    db.session.commit()
    flash("Eintrag hinzugefügt.", "success")
    return redirect(url_for("dashboard", date=day_str))


@app.route("/diary/<int:entry_id>/delete", methods=["POST"])
def diary_delete(entry_id):
    entry = DiaryEntry.query.get_or_404(entry_id)
    day_str = entry.date.isoformat()
    db.session.delete(entry)
    db.session.commit()
    flash("Eintrag gelöscht.", "success")
    return redirect(url_for("dashboard", date=day_str))


@app.route("/settings", methods=["GET", "POST"])
def settings():
    targets = DailyTarget.query.order_by(DailyTarget.id).all()
    if request.method == "POST":
        for t in targets:
            val = request.form.get(f"target_{t.nutrient}")
            if val is not None:
                t.target_value = float(val)
            lim = request.form.get(f"limit_{t.nutrient}")
            t.is_upper_limit = lim == "on"
        db.session.commit()
        flash("Zielwerte gespeichert.", "success")
        return redirect(url_for("settings"))
    return render_template("settings.html", targets=targets)


@app.route("/api/foods/search")
def api_food_search():
    q = request.args.get("q", "").strip()
    if len(q) < 1:
        return jsonify([])
    foods = Food.query.filter(Food.name.ilike(f"%{q}%")).limit(15).all()
    return jsonify([{"id": f.id, "name": f.name, "brand": f.brand,
                      "calories": f.calories} for f in foods])


@app.route("/ocr", methods=["POST"])
def ocr_upload():
    if "image" not in request.files:
        flash("Kein Bild hochgeladen.", "danger")
        return redirect(request.referrer or url_for("food_add"))

    file = request.files["image"]
    if file.filename == "":
        flash("Kein Bild ausgewählt.", "danger")
        return redirect(request.referrer or url_for("food_add"))

    try:
        import pytesseract
        from PIL import Image

        img = Image.open(file.stream)
        text = pytesseract.image_to_string(img, lang="deu")
        parsed = parse_nutrition_text(text)
        return render_template("food_form.html", food=None, ocr_data=parsed, ocr_text=text)
    except Exception as e:
        flash(f"OCR-Fehler: {e}", "danger")
        return redirect(url_for("food_add"))


@app.route("/burn/save", methods=["POST"])
def burn_save():
    day_str = request.form.get("date", date.today().isoformat())
    day = date.fromisoformat(day_str)
    val = float(request.form.get("calories_burned") or 0)
    burn = DailyBurn.query.filter_by(date=day).first()
    if burn:
        burn.calories_burned = val
    else:
        burn = DailyBurn(date=day, calories_burned=val)
        db.session.add(burn)
    db.session.commit()
    flash("Verbrannte Kalorien gespeichert.", "success")
    return redirect(url_for("dashboard", date=day_str))


@app.route("/api/chart/nutrient")
def api_chart_nutrient():
    period = request.args.get("period", "7")
    nutrient = request.args.get("nutrient", "calories")
    try:
        days = int(period)
    except ValueError:
        days = 7
    if days not in (7, 30, 365):
        days = 7

    valid_nutrients = [n[0] for n in NUTRIENTS]
    if nutrient not in valid_nutrients:
        nutrient = "calories"

    today_d = date.today()
    start = today_d - timedelta(days=days - 1)

    target_row = DailyTarget.query.filter_by(nutrient=nutrient).first()
    target_val = target_row.target_value if target_row else 0
    is_limit = target_row.is_upper_limit if target_row else False
    unit = target_row.unit if target_row else "g"

    burns = {}
    if nutrient == "calories":
        burns = {b.date: b.calories_burned
                 for b in DailyBurn.query.filter(DailyBurn.date >= start).all()}

    entries = DiaryEntry.query.filter(DiaryEntry.date >= start).all()
    intake_by_day = {}
    for e in entries:
        val = getattr(e.food, nutrient, 0) * e.amount_g / 100.0
        intake_by_day[e.date] = intake_by_day.get(e.date, 0) + val

    labels = []
    intakes = []
    diffs = []
    cumulative = []
    running_total = 0.0
    for i in range(days):
        d = start + timedelta(days=i)
        intake = round(intake_by_day.get(d, 0), 1)
        if nutrient == "calories":
            burned = burns.get(d, target_val)
            diff = round(intake - burned, 1)
        else:
            diff = round(intake - target_val, 1)
        running_total += diff
        fmt = d.strftime("%d.%m.") if days <= 30 else d.strftime("%d.%m.%y")
        labels.append(fmt)
        intakes.append(intake)
        diffs.append(diff)
        cumulative.append(round(running_total, 1))

    return jsonify({
        "labels": labels,
        "intakes": intakes,
        "diffs": diffs,
        "cumulative": cumulative,
        "target": target_val,
        "nutrient": nutrient,
        "unit": unit,
        "is_limit": is_limit,
    })


def parse_nutrition_text(text):
    result = {}
    patterns = {
        "calories": r"(?:energie|brennwert|kalorien|energy).*?(\d+[\.,]?\d*)\s*(?:kcal|kj)",
        "fat": r"(?:fett|fat)\s*(\d+[\.,]?\d*)\s*g",
        "saturated_fat": r"(?:gesättigt|davon\s+gesättigt|saturated).*?(\d+[\.,]?\d*)\s*g",
        "carbs": r"(?:kohlenhydrat|carbohydrat).*?(\d+[\.,]?\d*)\s*g",
        "sugar": r"(?:zucker|davon\s+zucker|sugar).*?(\d+[\.,]?\d*)\s*g",
        "protein": r"(?:eiweiß|protein).*?(\d+[\.,]?\d*)\s*g",
        "fiber": r"(?:ballast|fibre|fiber).*?(\d+[\.,]?\d*)\s*g",
        "salt": r"(?:salz|salt).*?(\d+[\.,]?\d*)\s*g",
    }
    lower = text.lower()
    for key, pattern in patterns.items():
        m = re.search(pattern, lower)
        if m:
            result[key] = float(m.group(1).replace(",", "."))
    return result


with app.app_context():
    db.create_all()
    seed_targets()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
