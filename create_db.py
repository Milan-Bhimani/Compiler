from app import app, db
from models import User, Document, Problem, Progress

with app.app_context():
    # Drop all tables
    db.drop_all()
    # Create the database and the tables
    db.create_all()

print("Database tables created.")
