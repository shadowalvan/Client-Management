"""
Clients Module - CRUD Operations

Handles all client-related routes:
- List all clients with contact counts
- Create new clients (with auto-generated client codes)
- Update client information
- Delete clients
- Link/unlink contacts to clients (many-to-many relationship)
"""

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
from services.client_code_service import generate_client_code


bp = Blueprint("clients", __name__, url_prefix="/clients")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _get_client_or_404(client_id):
    """
    Helper: Fetch a client by ID or return 404 if not found.
    
    Used across multiple routes to ensure client exists before operations.
    """
    db = get_db()
    cur = db.execute(
        "SELECT id, name, client_code FROM clients WHERE id = ?", (client_id,)
    )
    client = cur.fetchone()
    if client is None:
        abort(404)
    return client


# ============================================================================
# CRUD OPERATIONS - READ
# ============================================================================

@bp.route("/", methods=["GET"])
def list_clients():
    """
    List All Clients
    
    Displays all clients ordered by name (ASC) with:
    - Client name
    - Client code (auto-generated)
    - Number of linked contacts (counts many-to-many relationships)
    
    Uses LEFT JOIN to include clients with zero contacts (count = 0).
    """
    db = get_db()
    cur = db.execute(
        """
        SELECT c.id,
               c.name,
               c.client_code,
               COUNT(DISTINCT cc.contact_id) AS contact_count
        FROM clients c
        LEFT JOIN client_contacts cc ON c.id = cc.client_id
        GROUP BY c.id, c.name, c.client_code
        ORDER BY c.name ASC
        """
    )
    clients = cur.fetchall()
    return render_template("clients_list.html", clients=clients)


# ============================================================================
# CRUD OPERATIONS - CREATE
# ============================================================================

@bp.route("/new", methods=["GET"])
def new_client():
    """
    New Client Form
    
    Displays the client creation form with two tabs:
    - General: Name field (client code hidden until saved)
    - Contact(s): Shows "Save client to link contacts" message
    """
    return render_template(
        "client_form.html",
        client=None,
        linked_contacts=[],
        available_contacts=[],
        errors={},
        form_data={},
        is_new=True,
    )


@bp.route("/", methods=["POST"])
def create_client():
    """
    Create New Client
    
    Validates client name (required), generates unique client code,
    and redirects to edit page where client code becomes visible.
    
    Business Rules:
    - Name is required (server-side validation)
    - Client code is auto-generated (6 chars: 3 alpha + 3 numeric)
    - Client code is unique across all clients
    """
    db = get_db()
    name = (request.form.get("name") or "").strip()
    errors = {}

    if not name:
        errors["name"] = "Name is required."

    if errors:
        return render_template(
            "client_form.html",
            client=None,
            linked_contacts=[],
            available_contacts=[],
            errors=errors,
            form_data={"name": name},
            is_new=True,
        )

    client_code = generate_client_code(db, name)
    cur = db.execute(
        "INSERT INTO clients (name, client_code) VALUES (?, ?)",
        (name, client_code),
    )
    db.commit()
    client_id = cur.lastrowid

    flash("Client created successfully.", "success")
    return redirect(url_for("clients.edit_client", client_id=client_id))


# ============================================================================
# CRUD OPERATIONS - UPDATE
# ============================================================================

@bp.route("/<int:client_id>/edit", methods=["GET"])
def edit_client(client_id):
    """
    Edit Client Form
    
    Displays client edit form with two tabs:
    - General: Name (editable) and Client Code (read-only, auto-generated)
    - Contact(s): Lists linked contacts with unlink actions + dropdown to link new contacts
    
    Queries:
    1. Linked contacts: Contacts already associated with this client
    2. Available contacts: Contacts not yet linked (for dropdown)
    """
    db = get_db()
    client = _get_client_or_404(client_id)

    # Query 1: Get contacts already linked to this client
    # Ordered by Full Name (Surname, Name) for consistent display
    cur = db.execute(
        """
        SELECT ct.id,
               ct.name,
               ct.surname,
               ct.email
        FROM contacts ct
        JOIN client_contacts cc ON ct.id = cc.contact_id
        WHERE cc.client_id = ?
        ORDER BY ct.surname ASC, ct.name ASC
        """,
        (client_id,),
    )
    linked_contacts = cur.fetchall()

    # Query 2: Get contacts NOT yet linked to this client
    # Used to populate the "Link existing contact" dropdown
    cur = db.execute(
        """
        SELECT ct.id,
               ct.name,
               ct.surname,
               ct.email
        FROM contacts ct
        WHERE ct.id NOT IN (
            SELECT contact_id FROM client_contacts WHERE client_id = ?
        )
        ORDER BY ct.surname ASC, ct.name ASC
        """,
        (client_id,),
    )
    available_contacts = cur.fetchall()

    return render_template(
        "client_form.html",
        client=client,
        linked_contacts=linked_contacts,
        available_contacts=available_contacts,
        errors={},
        form_data={"name": client["name"]},
        is_new=False,
    )


@bp.route("/<int:client_id>", methods=["POST"])
def update_client(client_id):
    """
    Update Client Information
    
    Updates client name with validation. On error, re-renders form with
    error messages and preserves linked/available contacts data.
    
    Note: Client code cannot be changed (it's read-only and system-generated).
    """
    db = get_db()
    client = _get_client_or_404(client_id)

    name = (request.form.get("name") or "").strip()
    errors = {}

    if not name:
        errors["name"] = "Name is required."

    if errors:
        # On validation error: rebuild contact lists for form re-render
        cur = db.execute(
            """
            SELECT ct.id,
                   ct.name,
                   ct.surname,
                   ct.email
            FROM contacts ct
            JOIN client_contacts cc ON ct.id = cc.contact_id
            WHERE cc.client_id = ?
            ORDER BY ct.surname ASC, ct.name ASC
            """,
            (client_id,),
        )
        linked_contacts = cur.fetchall()

        cur = db.execute(
            """
            SELECT ct.id,
                   ct.name,
                   ct.surname,
                   ct.email
            FROM contacts ct
            WHERE ct.id NOT IN (
                SELECT contact_id FROM client_contacts WHERE client_id = ?
            )
            ORDER BY ct.surname ASC, ct.name ASC
            """,
            (client_id,),
        )
        available_contacts = cur.fetchall()

        return render_template(
            "client_form.html",
            client=client,
            linked_contacts=linked_contacts,
            available_contacts=available_contacts,
            errors=errors,
            form_data={"name": name},
            is_new=False,
        )

    db.execute(
        "UPDATE clients SET name = ? WHERE id = ?",
        (name, client_id),
    )
    db.commit()
    flash("Client updated successfully.", "success")
    return redirect(url_for("clients.edit_client", client_id=client_id))


# ============================================================================
# MANY-TO-MANY RELATIONSHIP OPERATIONS
# ============================================================================

@bp.route("/<int:client_id>/link_contact", methods=["POST"])
def link_contact(client_id):
    """
    Link Contact to Client
    
    Creates a many-to-many relationship between a client and a contact.
    Uses INSERT OR IGNORE to prevent duplicate links (enforced by composite PK).
    
    After linking, redirects back to edit page where the new link appears.
    """
    db = get_db()
    _get_client_or_404(client_id)

    contact_id = request.form.get("contact_id")
    if contact_id:
        # INSERT OR IGNORE prevents errors if link already exists
        db.execute(
            "INSERT OR IGNORE INTO client_contacts (client_id, contact_id) VALUES (?, ?)",
            (client_id, contact_id),
        )
        db.commit()
        flash("Contact linked to client.", "success")

    return redirect(url_for("clients.edit_client", client_id=client_id))


@bp.route("/<int:client_id>/unlink_contact/<int:contact_id>", methods=["GET"])
def unlink_contact(client_id, contact_id):
    """
    Unlink Contact from Client
    
    Removes the many-to-many relationship between a client and a contact.
    The contact and client records themselves remain unchanged.
    
    After unlinking, the contact count in the list view updates automatically.
    """
    db = get_db()
    _get_client_or_404(client_id)

    db.execute(
        "DELETE FROM client_contacts WHERE client_id = ? AND contact_id = ?",
        (client_id, contact_id),
    )
    db.commit()
    flash("Contact unlinked from client.", "success")
    return redirect(url_for("clients.edit_client", client_id=client_id))


# ============================================================================
# CRUD OPERATIONS - DELETE
# ============================================================================

@bp.route("/<int:client_id>/delete", methods=["POST"])
def delete_client(client_id):
    """
    Delete Client
    
    Permanently deletes a client record. Foreign key constraints with CASCADE
    automatically remove all associated links in the client_contacts junction table.
    
    After deletion, redirects to clients list page.
    """
    db = get_db()
    _get_client_or_404(client_id)

    db.execute("DELETE FROM clients WHERE id = ?", (client_id,))
    db.commit()
    flash("Client deleted successfully.", "success")
    return redirect(url_for("clients.list_clients"))


