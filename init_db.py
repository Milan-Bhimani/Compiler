from app import db
from models import User, Document

db.create_all()
print("Database initialized!")
