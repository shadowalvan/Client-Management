"""
Contacts Module - CRUD Operations

Handles all contact-related routes:
- List all contacts with client counts
- Create new contacts (with email validation and uniqueness check)
- Update contact information
- Delete contacts
- Link/unlink clients to contacts (many-to-many relationship)
"""

import re

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    abort,
)

from db.db import get_db


bp = Blueprint("contacts", __name__, url_prefix="/contacts")

# Email validation regex: ensures basic email format (user@domain.tld)
EMAIL_REGEX = re.compile(r"^[^@]+@[^@]+\.[^@]+$")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _get_contact_or_404(contact_id):
    """
    Helper: Fetch a contact by ID or return 404 if not found.
    
    Used across multiple routes to ensure contact exists before operations.
    """
    db = get_db()
    cur = db.execute(
        "SELECT id, name, surname, email FROM contacts WHERE id = ?",
        (contact_id,),
    )
    contact = cur.fetchone()
    if contact is None:
        abort(404)
    return contact


# ============================================================================
# CRUD OPERATIONS - READ
# ============================================================================

@bp.route("/", methods=["GET"])
def list_contacts():
    """
    List All Contacts
    
    Displays all contacts ordered by Full Name (Surname, Name ASC) with:
    - Contact name and surname
    - Email address
    - Number of linked clients (counts many-to-many relationships)
    
    Uses LEFT JOIN to include contacts with zero clients (count = 0).
    """
    db = get_db()
    cur = db.execute(
        """
        SELECT ct.id,
               ct.name,
               ct.surname,
               ct.email,
               COUNT(DISTINCT cc.client_id) AS client_count
        FROM contacts ct
        LEFT JOIN client_contacts cc ON ct.id = cc.contact_id
        GROUP BY ct.id, ct.name, ct.surname, ct.email
        ORDER BY ct.surname ASC, ct.name ASC
        """
    )
    contacts = cur.fetchall()
    return render_template("contacts_list.html", contacts=contacts)


# ============================================================================
# CRUD OPERATIONS - CREATE
# ============================================================================

@bp.route("/new", methods=["GET"])
def new_contact():
    """
    New Contact Form
    
    Displays the contact creation form with two tabs:
    - General: Name, Surname, Email fields (all required)
    - Client(s): Shows "Save contact to link clients" message
    """
    return render_template(
        "contact_form.html",
        contact=None,
        linked_clients=[],
        available_clients=[],
        errors={},
        form_data={},
        is_new=True,
    )


@bp.route("/", methods=["POST"])
def create_contact():
    """
    Create New Contact
    
    Validates contact data with server-side validation:
    - Name: required
    - Surname: required
    - Email: required, must be valid format, must be unique across all contacts
    
    On success, redirects to edit page. On error, re-renders form with error messages.
    """
    db = get_db()
    name = (request.form.get("name") or "").strip()
    surname = (request.form.get("surname") or "").strip()
    email = (request.form.get("email") or "").strip()

    errors = {}
    
    # Server-side validation: Name required
    if not name:
        errors["name"] = "Name is required."
    
    # Server-side validation: Surname required
    if not surname:
        errors["surname"] = "Surname is required."
    
    # Server-side validation: Email required, format check, uniqueness check
    if not email:
        errors["email"] = "Email is required."
    elif not EMAIL_REGEX.match(email):
        errors["email"] = "Email is not valid."
    else:
        # Check email uniqueness in database
        cur = db.execute(
            "SELECT 1 FROM contacts WHERE email = ?",
            (email,),
        )
        if cur.fetchone():
            errors["email"] = "Email must be unique."

    if errors:
        return render_template(
            "contact_form.html",
            contact=None,
            linked_clients=[],
            available_clients=[],
            errors=errors,
            form_data={"name": name, "surname": surname, "email": email},
            is_new=True,
        )

    cur = db.execute(
        "INSERT INTO contacts (name, surname, email) VALUES (?, ?, ?)",
        (name, surname, email),
    )
    db.commit()
    contact_id = cur.lastrowid

    flash("Contact created successfully.", "success")
    return redirect(url_for("contacts.edit_contact", contact_id=contact_id))


# ============================================================================
# CRUD OPERATIONS - UPDATE
# ============================================================================

@bp.route("/<int:contact_id>/edit", methods=["GET"])
def edit_contact(contact_id):
    """
    Edit Contact Form
    
    Displays contact edit form with two tabs:
    - General: Name, Surname, Email (all editable with validation)
    - Client(s): Lists linked clients with unlink actions + dropdown to link new clients
    
    Queries:
    1. Linked clients: Clients already associated with this contact
    2. Available clients: Clients not yet linked (for dropdown)
    """
    db = get_db()
    contact = _get_contact_or_404(contact_id)

    # Query 1: Get clients already linked to this contact
    cur = db.execute(
        """
        SELECT cl.id,
               cl.name,
               cl.client_code
        FROM clients cl
        JOIN client_contacts cc ON cl.id = cc.client_id
        WHERE cc.contact_id = ?
        ORDER BY cl.name ASC
        """,
        (contact_id,),
    )
    linked_clients = cur.fetchall()

    # Query 2: Get clients NOT yet linked to this contact
    # Used to populate the "Link existing client" dropdown
    cur = db.execute(
        """
        SELECT cl.id,
               cl.name,
               cl.client_code
        FROM clients cl
        WHERE cl.id NOT IN (
            SELECT client_id FROM client_contacts WHERE contact_id = ?
        )
        ORDER BY cl.name ASC
        """,
        (contact_id,),
    )
    available_clients = cur.fetchall()

    return render_template(
        "contact_form.html",
        contact=contact,
        linked_clients=linked_clients,
        available_clients=available_clients,
        errors={},
        form_data={
            "name": contact["name"],
            "surname": contact["surname"],
            "email": contact["email"],
        },
        is_new=False,
    )


@bp.route("/<int:contact_id>", methods=["POST"])
def update_contact(contact_id):
    """
    Update Contact Information
    
    Updates contact name, surname, and email with full validation.
    Email uniqueness check excludes the current contact's ID to allow
    saving unchanged email addresses.
    
    On error, re-renders form with error messages and preserves linked/available clients.
    """
    db = get_db()
    contact = _get_contact_or_404(contact_id)

    name = (request.form.get("name") or "").strip()
    surname = (request.form.get("surname") or "").strip()
    email = (request.form.get("email") or "").strip()

    errors = {}
    if not name:
        errors["name"] = "Name is required."
    if not surname:
        errors["surname"] = "Surname is required."
    if not email:
        errors["email"] = "Email is required."
    elif not EMAIL_REGEX.match(email):
        errors["email"] = "Email is not valid."
    else:
        # Email uniqueness check: exclude current contact's ID
        cur = db.execute(
            "SELECT 1 FROM contacts WHERE email = ? AND id <> ?",
            (email, contact_id),
        )
        if cur.fetchone():
            errors["email"] = "Email must be unique."

    if errors:
        cur = db.execute(
            """
            SELECT cl.id,
                   cl.name,
                   cl.client_code
            FROM clients cl
            JOIN client_contacts cc ON cl.id = cc.client_id
            WHERE cc.contact_id = ?
            ORDER BY cl.name ASC
            """,
            (contact_id,),
        )
        linked_clients = cur.fetchall()

        cur = db.execute(
            """
            SELECT cl.id,
                   cl.name,
                   cl.client_code
            FROM clients cl
            WHERE cl.id NOT IN (
                SELECT client_id FROM client_contacts WHERE contact_id = ?
            )
            ORDER BY cl.name ASC
            """,
            (contact_id,),
        )
        available_clients = cur.fetchall()

        return render_template(
            "contact_form.html",
            contact=contact,
            linked_clients=linked_clients,
            available_clients=available_clients,
            errors=errors,
            form_data={"name": name, "surname": surname, "email": email},
            is_new=False,
        )

    db.execute(
        "UPDATE contacts SET name = ?, surname = ?, email = ? WHERE id = ?",
        (name, surname, email, contact_id),
    )
    db.commit()
    flash("Contact updated successfully.", "success")
    return redirect(url_for("contacts.edit_contact", contact_id=contact_id))


# ============================================================================
# MANY-TO-MANY RELATIONSHIP OPERATIONS
# ============================================================================

@bp.route("/<int:contact_id>/link_client", methods=["POST"])
def link_client(contact_id):
    """
    Link Client to Contact
    
    Creates a many-to-many relationship between a contact and a client.
    Uses INSERT OR IGNORE to prevent duplicate links (enforced by composite PK).
    
    After linking, redirects back to edit page where the new link appears.
    """
    db = get_db()
    _get_contact_or_404(contact_id)

    client_id = request.form.get("client_id")
    if client_id:
        # INSERT OR IGNORE prevents errors if link already exists
        db.execute(
            "INSERT OR IGNORE INTO client_contacts (client_id, contact_id) VALUES (?, ?)",
            (client_id, contact_id),
        )
        db.commit()
        flash("Client linked to contact.", "success")

    return redirect(url_for("contacts.edit_contact", contact_id=contact_id))


@bp.route("/<int:contact_id>/unlink_client/<int:client_id>", methods=["GET"])
def unlink_client(contact_id, client_id):
    """
    Unlink Client from Contact
    
    Removes the many-to-many relationship between a contact and a client.
    The contact and client records themselves remain unchanged.
    
    After unlinking, the client count in the list view updates automatically.
    """
    db = get_db()
    _get_contact_or_404(contact_id)

    db.execute(
        "DELETE FROM client_contacts WHERE client_id = ? AND contact_id = ?",
        (client_id, contact_id),
    )
    db.commit()
    flash("Client unlinked from contact.", "success")
    return redirect(url_for("contacts.edit_contact", contact_id=contact_id))


# ============================================================================
# CRUD OPERATIONS - DELETE
# ============================================================================

@bp.route("/<int:contact_id>/delete", methods=["POST"])
def delete_contact(contact_id):
    """
    Delete Contact
    
    Permanently deletes a contact record. Foreign key constraints with CASCADE
    automatically remove all associated links in the client_contacts junction table.
    
    After deletion, redirects to contacts list page.
    """
    db = get_db()
    _get_contact_or_404(contact_id)

    db.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
    db.commit()
    flash("Contact deleted successfully.", "success")
    return redirect(url_for("contacts.list_contacts"))


