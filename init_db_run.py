from app import create_app
from db.db import init_db

app = create_app()

with app.app_context():
    init_db()

print("Database initialized successfully.")