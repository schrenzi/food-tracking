from flask_sqlalchemy import SQLAlchemy
from datetime import date

db = SQLAlchemy()


class Food(db.Model):
    __tablename__ = "foods"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    brand = db.Column(db.String(200), default="")
    calories = db.Column(db.Float, default=0)
    fat = db.Column(db.Float, default=0)
    saturated_fat = db.Column(db.Float, default=0)
    carbs = db.Column(db.Float, default=0)
    sugar = db.Column(db.Float, default=0)
    protein = db.Column(db.Float, default=0)
    fiber = db.Column(db.Float, default=0)
    salt = db.Column(db.Float, default=0)
    serving_size = db.Column(db.Float, default=100)
    diary_entries = db.relationship("DiaryEntry", backref="food", lazy=True)


class DailyTarget(db.Model):
    __tablename__ = "daily_targets"
    id = db.Column(db.Integer, primary_key=True)
    nutrient = db.Column(db.String(50), unique=True, nullable=False)
    label = db.Column(db.String(100), nullable=False)
    target_value = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(10), default="g")
    is_upper_limit = db.Column(db.Boolean, default=False)


class DiaryEntry(db.Model):
    __tablename__ = "diary_entries"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=date.today)
    meal_type = db.Column(db.String(20), nullable=False, default="snack")
    food_id = db.Column(db.Integer, db.ForeignKey("foods.id"), nullable=False)
    amount_g = db.Column(db.Float, nullable=False, default=100)


class DailyBurn(db.Model):
    __tablename__ = "daily_burns"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, unique=True, nullable=False)
    calories_burned = db.Column(db.Float, nullable=False, default=0)
