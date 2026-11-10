from fastmcp import FastMCP
from datetime import datetime
import math
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "expenses.db")
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")

mcp = FastMCP("ExpenseTracker")

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

def clean_date(value: str) -> str:
    '''Return the date as YYYY-MM-DD, or raise a clear error.'''
    try:
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
    except ValueError:
        raise ValueError(f"Invalid date '{value}'. Use YYYY-MM-DD, for example 2026-11-09.")

def clean_range(start_date: str, end_date: str):
    '''Check both dates and make sure the start is not after the end.'''
    start = clean_date(start_date)
    end = clean_date(end_date)
    if start > end:
        raise ValueError(f"start_date ({start}) is after end_date ({end}).")
    return start, end

def clean_category(value: str) -> str:
    '''Trim, lowercase, and reject a blank category.'''
    category = value.strip().lower()
    if not category:
        raise ValueError("Category cannot be blank.")
    return category

@mcp.tool()
def add_expense(date: str, amount: float, category: str, subcategory: str = "", note: str = ""):
    '''Add a new expense entry to the database. Date format is YYYY-MM-DD.'''
    date = clean_date(date)
    category = clean_category(category)
    if not math.isfinite(amount) or amount <= 0:
        raise ValueError("Amount must be a number greater than 0.")

    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            "INSERT INTO expenses(date, amount, category, subcategory, note) VALUES (?,?,?,?,?)",
            (date, amount, category, subcategory, note)
        )
        return {"status": "ok", "id": cur.lastrowid}

@mcp.tool()
def list_expenses(start_date: str, end_date: str):
    '''List expense entries within an inclusive date range. Dates are YYYY-MM-DD.'''
    start_date, end_date = clean_range(start_date, end_date)

    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            """
            SELECT id, date, amount, category, subcategory, note
            FROM expenses
            WHERE date BETWEEN ? AND ?
            ORDER BY id ASC
            """,
            (start_date, end_date)
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

@mcp.tool()
def summarize(start_date: str, end_date: str, category: str | None = None):
    '''Summarize expenses by category within an inclusive date range. Dates are YYYY-MM-DD.'''
    start_date, end_date = clean_range(start_date, end_date)

    with sqlite3.connect(DB_PATH) as c:
        query = (
            """
            SELECT category, SUM(amount) AS total_amount
            FROM expenses
            WHERE date BETWEEN ? AND ?
            """
        )
        params = [start_date, end_date]

        if category:
            query += " AND category = ?"
            params.append(clean_category(category))

        query += " GROUP BY category ORDER BY category ASC"

        cur = c.execute(query, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

@mcp.resource("expense://categories", mime_type="application/json")
def categories():
    # Read fresh each time so you can edit the file without restarting
    with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
        return f.read()

def main():
    mcp.run(transport="http", host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()