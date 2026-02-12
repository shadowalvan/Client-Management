"""
Client Code Generation Service

Implements automatic client code generation with the following rules:
- Format: 6 characters total (3 uppercase letters + 3 digits)
- Alpha prefix: Derived from client name initials
- Numeric suffix: Increments sequentially (001, 002, 003...) per alpha prefix
- Uniqueness: Ensures each code is unique across all clients

Examples:
- "First National Bank" -> FNB001
- "IT Services" -> ITS001
- "A" -> AAB001 (padded with A-Z)
"""


def _build_alpha_prefix(name: str) -> str:
    """
    Build a 3-letter uppercase alpha prefix from the client name.

    Business Rules:
    - Extract first letter of each word: "First National Bank" -> "FNB"
    - If name has fewer than 3 words, pad with alphabet (A-Z)
    - Examples:
      * "First National Bank" -> "FNB"
      * "IT Services" -> "ITS"
      * "IT" -> "ITA" (padded)
      * "A" -> "AAB" (padded)
    """
    if not name:
        initials = ""
    else:
        words = [w for w in name.strip().split() if w]
        initials = "".join(w[0] for w in words if w[0].isalpha()).upper()

    letters = list(initials[:3])
    next_char_ord = ord("A")
    while len(letters) < 3:
        letters.append(chr(next_char_ord))
        next_char_ord += 1
        if next_char_ord > ord("Z"):
            next_char_ord = ord("A")

    return "".join(letters)


def generate_client_code(db, name: str) -> str:
    """
    Generate a unique 6-character client code (3 alpha + 3 numeric).

    Process:
    1. Build 3-letter alpha prefix from client name
    2. Find the highest numeric suffix for that prefix in the database
    3. Increment by 1 (or start at 001 if none exists)
    4. Verify uniqueness (handle edge cases/race conditions)
    5. Return the final code (e.g., "FNB001", "FNB002", "PRO123")

    Parameters:
        db: Database connection object
        name: Client name string

    Returns:
        Unique 6-character client code (e.g., "FNB001")
    """
    prefix = _build_alpha_prefix(name)

    # Step 1: Find the highest existing code with this prefix
    # Uses LIKE pattern matching: "FNB___" matches "FNB001", "FNB002", etc.
    cursor = db.execute(
        """
        SELECT client_code
        FROM clients
        WHERE client_code LIKE ?
        ORDER BY client_code DESC
        LIMIT 1
        """,
        (prefix + "___",),
    )
    row = cursor.fetchone()

    # Step 2: Extract numeric part and increment
    if row:
        last_code: str = row["client_code"]
        try:
            # Extract last 3 characters and convert to integer
            last_num = int(last_code[3:])
        except ValueError:
            # Fallback if code format is unexpected
            last_num = 0
        num = last_num + 1
    else:
        # No existing codes with this prefix - start at 001
        num = 1

    # Step 3: Ensure absolute uniqueness (handles race conditions)
    # Loop until we find a code that doesn't exist in the database
    while True:
        code = f"{prefix}{num:03d}"  # Format: "FNB001", "FNB002", etc.
        cursor = db.execute(
            "SELECT 1 FROM clients WHERE client_code = ?", (code,)
        )
        if not cursor.fetchone():
            return code  # Found unique code
        num += 1  # Try next number if conflict exists
