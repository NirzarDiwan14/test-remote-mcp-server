from fastmcp import FastMCP
import os
import re
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "expenses.db")
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")

mcp = FastMCP("Remote-Expense-Tracker")

# Blocked SQL patterns — prevents schema changes and table destruction
BLOCKED_PATTERNS = [
    r"\bDROP\b",
    r"\bALTER\b",
    r"\bCREATE\b",
    r"\bTRUNCATE\b",
    r"\bRENAME\b",
    r"\bATTACH\b",
    r"\bDETACH\b",
    r"\bVACUUM\b",
    r"\bREINDEX\b",
    r"\bPRAGMA\b",
]

def init_db():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS expenses(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT DEFAULT '',
                note TEXT DEFAULT ''
            )
        """)

init_db()

def _is_query_safe(sql: str) -> tuple[bool, str]:
    """Check if a SQL query is safe to execute.
    
    Allows: SELECT, INSERT, UPDATE, DELETE (content manipulation).
    Blocks: DROP, ALTER, CREATE, TRUNCATE, etc. (schema/table changes).
    """
    normalised = sql.strip().upper()
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, normalised):
            keyword = pattern.replace(r"\b", "")
            return False, f"Blocked: '{keyword}' statements are not allowed."
    return True, ""


@mcp.tool()
def execute_sql(query: str):
    '''Execute a raw SQL query against the expenses SQLite database and return the results.
    
    The database has a single table called `expenses` with the following schema:
        id          INTEGER PRIMARY KEY AUTOINCREMENT
        date        TEXT NOT NULL          -- format: YYYY-MM-DD
        amount      REAL NOT NULL
        category    TEXT NOT NULL
        subcategory TEXT DEFAULT ''
        note        TEXT DEFAULT ''
    
    Allowed operations: SELECT, INSERT, UPDATE, DELETE.
    Blocked operations: DROP, ALTER, CREATE, TRUNCATE, RENAME (schema changes are forbidden).
    
    Returns a dict with:
        - "columns" and "rows" for SELECT queries
        - "rows_affected" and optionally "last_row_id" for write queries
    '''
    safe, reason = _is_query_safe(query)
    if not safe:
        return {"error": reason}

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.execute(query)

            # If the query returns rows (SELECT, etc.)
            if cur.description:
                cols = [d[0] for d in cur.description]
                rows = [dict(zip(cols, r)) for r in cur.fetchall()]
                return {"columns": cols, "rows": rows, "row_count": len(rows)}
            
            # Write query (INSERT / UPDATE / DELETE)
            conn.commit()
            result = {"status": "ok", "rows_affected": cur.rowcount}
            if cur.lastrowid:
                result["last_row_id"] = cur.lastrowid
            return result

    except sqlite3.Error as e:
        return {"error": str(e)}


@mcp.resource("expense://categories", mime_type="application/json")
def categories():
    # Read fresh each time so you can edit the file without restarting
    with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    mcp.run(transport = "http",host = "0.0.0.0",port = 8000)