import sqlite3

DB_FILE = 'hrajty.db'

# Funkce pro vytvoření tabulky, pokud neexistuje
def create_table():
    """Vytvoří tabulku v databázi, pokud neexistuje."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            title TEXT,
            content TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Zavolání funkce pro vytvoření tabulky při spuštění aplikace
create_table()

def search_pages(keyword):
    """Hledá stránky podle zadaného klíčového slova v obsahu."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT url, title, content FROM pages WHERE content LIKE ?",
        ('%' + keyword + '%',)
    )
    results = cursor.fetchall()
    conn.close()
    return results

def suggest_terms(prefix, limit=10):
    """Navrhuje názvy stránek, které začínají zadaným prefixem."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DISTINCT title FROM pages WHERE title LIKE ? LIMIT ?",
        (prefix + '%', limit)
    )
    titles = [row[0] for row in cursor.fetchall()]
    conn.close()
    return titles

def get_statistics():
    """Vrací statistiky o počtu stránek v databázi."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM pages")
    count = cursor.fetchone()[0]
    conn.close()
    return count, count  # (stránky, karty)
