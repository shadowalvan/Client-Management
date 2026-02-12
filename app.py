"""
Client-Contact Manager - Flask Application

A CRUD application demonstrating a many-to-many relationship between
Clients and Contacts with automatic client code generation.

Architecture: MVC-style with Flask blueprints, SQLite database,
and server-side validation.
"""

from pathlib import Path

from flask import Flask, redirect, url_for

from db.db import close_db, init_db, get_db
from routes.clients import bp as clients_bp
from routes.contacts import bp as contacts_bp


def create_app():
    """
    Application Factory Pattern
    
    Creates and configures the Flask application instance.
    Sets up database connection, registers blueprints, and defines utility routes.
    """
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY="dev",  # replace with a secure key for production
    )

    # Default SQLite database in the project root
    db_path = Path(app.root_path).parent / "client_contact_manager.sqlite"
    app.config["DATABASE"] = str(db_path)

    # Ensure instance folder exists (for compatibility)
    try:
        Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

    # Teardown
    app.teardown_appcontext(close_db)

    # Blueprints
    app.register_blueprint(clients_bp)
    app.register_blueprint(contacts_bp)

    # ============================================================================
    # UTILITY ROUTES
    # ============================================================================
    
    @app.route("/")
    def index():
        """Root route - redirects to clients list page."""
        return redirect(url_for("clients.list_clients"))

    @app.route("/init-db")
    def init_db_route():
        """
        Initialize Database Route
        
        Creates all database tables and indexes from schema.sql.
        Visit this route once after starting the app to set up the database.
        """
        init_db()
        return "Database initialized."

    @app.route("/seed-demo")
    def seed_demo():
        """
        Seed Demo Data Route
        
        Populates the database with sample clients, contacts, and relationships
        for demonstration purposes. Only runs if the database is empty.
        
        Creates:
        - 3 sample contacts (John Smith, Sarah Nguyen, Michael Brown)
        - 3 sample clients (First National Bank, Pro Logistics, IT Services)
        - Sample many-to-many relationships between clients and contacts
        """
        db = get_db()

        # Simple guard: only seed when there are no clients and contacts yet.
        cur = db.execute("SELECT COUNT(*) AS cnt FROM clients")
        client_count = cur.fetchone()["cnt"]
        cur = db.execute("SELECT COUNT(*) AS cnt FROM contacts")
        contact_count = cur.fetchone()["cnt"]

        if client_count > 0 or contact_count > 0:
            return "Seed skipped: data already exists."

        # Insert demo contacts
        contacts = [
            ("John", "Smith", "john.smith@example.com"),
            ("Sarah", "Nguyen", "sarah.nguyen@example.com"),
            ("Michael", "Brown", "michael.brown@example.com"),
        ]
        for name, surname, email in contacts:
            db.execute(
                "INSERT INTO contacts (name, surname, email) VALUES (?, ?, ?)",
                (name, surname, email),
            )

        # Insert demo clients with simple names; client codes will auto-generate
        from services.client_code_service import generate_client_code

        demo_clients = ["First National Bank", "Pro Logistics", "IT Services"]
        client_ids = []
        for cname in demo_clients:
            code = generate_client_code(db, cname)
            cur = db.execute(
                "INSERT INTO clients (name, client_code) VALUES (?, ?)",
                (cname, code),
            )
            client_ids.append(cur.lastrowid)

        # Link some demo relations
        cur = db.execute("SELECT id FROM contacts ORDER BY surname ASC, name ASC")
        contact_rows = cur.fetchall()
        if client_ids and contact_rows:
            # Link first client to all contacts
            for contact in contact_rows:
                db.execute(
                    "INSERT INTO client_contacts (client_id, contact_id) VALUES (?, ?)",
                    (client_ids[0], contact["id"]),
                )
            # Link second client to first contact
            if len(client_ids) > 1:
                db.execute(
                    "INSERT INTO client_contacts (client_id, contact_id) VALUES (?, ?)",
                    (client_ids[1], contact_rows[0]["id"]),
                )

        db.commit()
        return "Demo data seeded."

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)

