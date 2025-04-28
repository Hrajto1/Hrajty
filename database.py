import os
import sqlite3
from urllib.parse import urlparse
import psycopg2

# Lokální SQLite soubor
DB_FILE = 'hrajty.db'
# Pokud běží na Railway (nebo GH Actions), dostaneme toto URL
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_conn():
    """
    Vrátí připojení:
    - pokud je DATABASE_URL, použije psycopg2 (PostgreSQL)
    - jinak sqlite3 (lokálně)
    """
    if DATABASE_URL:
        # psycopg2 dokáže přijmout URL přímo
        return psycopg2.connect(DATABASE_URL, sslmode="require")
    else:
        # lokální vývoj
        return sqlite3.connect(DB_FILE)

def create_table():
    """Vytvoří tabulku pages, pokud neexistuje."""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pages (
            id SERIAL PRIMARY KEY,
            url TEXT UNIQUE,
            title TEXT,
            content TEXT
        )
    ''')
    conn.commit()
    conn.close()

# ihned vytvoříme tabulku při načtení modulu
create_table()

def search_pages(keyword):
    """Hledá URL, title a content podle klíčového slova v content."""
    conn = get_conn()
    cursor = conn.cursor()
    # u PostgreSQL použijeme ILIKE pro case-insensitive, u SQLite funguje LIKE
    op = "ILIKE" if DATABASE_URL else "LIKE"
    sql = f"SELECT url, title, content FROM pages WHERE content {op} %s"
    param = f"%{keyword}%"
    cursor.execute(sql, (param,))
    results = cursor.fetchall()
    conn.close()
    return results

def suggest_terms(prefix, limit=10):
    """Návrhy názvů (title) podle prefixu."""
    conn = get_conn()
    cursor = conn.cursor()
    op = "ILIKE" if DATABASE_URL else "LIKE"
    sql = f"SELECT DISTINCT title FROM pages WHERE title {op} %s LIMIT %s"
    cursor.execute(sql, (prefix + '%', limit))
    titles = [row[0] for row in cursor.fetchall()]
    conn.close()
    return titles

def get_statistics():
    """
    Vrací dvojici (registered_pages, registered_cards):
    - registered_pages = počet hlavních záznamů v pages
    - registered_cards  = totéž (můžeš rozšířit později)
    """
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM pages")
    count = cursor.fetchone()[0]
    conn.close()
    # prozatím jsou shodné
    return count, count
