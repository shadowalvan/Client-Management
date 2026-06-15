CLIENT–CONTACT MANAGER
This is a small Flask-based CRUD application built to demonstrate how to manage Clients and Contacts using a many-to-many relationship.

The application allows users to create clients and contacts, link them together, and manage those links in a simple and structured way.

WHAT THE APPLICATION DOES
The application allows users to create and manage clients.
The application allows users to create and manage contacts.
Clients and contacts can be linked and unlinked using a many-to-many relationship.
Client codes are generated automatically based on the client name and are guaranteed to be unique.
Server-side validation is implemented to ensure data accuracy.
Clear messages are displayed when no data exists "No clients found".
TECHNOLOGIES USED
Python
Flask
SQLite using Python’s built-in sqlite3 module
HTML with Jinja2 templates
Minimal CSS for layout and readability
TECHNOLOGIES USED
Python 3.9+ (any recent 3.x should work)
pip to install dependencies
Installation
From the project folder (Client Management):

pip install flask

Database initialization
Before running the app, initialize the database:
python init_db_run.py
This will create all required tables using the schema defined in db/schema.sql
Running the app
python app.py
Then in your browser:
Open http://localhost:5000/ to use the application.
This project reflects my approach to building structured, reliable applications with clear logic, validation, and maintainable code.
