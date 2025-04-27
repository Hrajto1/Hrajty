import requests
from bs4 import BeautifulSoup
import sqlite3
import time
import os
import csv
import socket
import zipfile
import io  # Tento import přidáme pro práci s io
from urllib.parse import urljoin, urlparse
from requests.exceptions import Timeout, ConnectionError, SSLError, RequestException
import urllib3

# Zakázání SSL varování (pro testování)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Konfigurace
DB_FILE = 'hrajty.db'
UMBRELLA_ZIP = 'http://s3-us-west-1.amazonaws.com/umbrella-static/top-1m.csv.zip'

# Konstanty pro retry
MAX_RETRIES = 1
RETRY_DELAY = 1  # sekundy

# Seznam domén, které nebudeme zkoušet
IGNORE_DOMAINS = ['amazonaws.com', 'microsoft.com', 'office.net', 'doubleclick.net']

def fetch_top_domains(n=20000):
    """Stahuje seznam top domén z Cisco Umbrella."""
    print("Stahuji seznam top domén z Cisco Umbrella…")
    r = requests.get(UMBRELLA_ZIP, stream=True, timeout=10)
    r.raise_for_status()
    # Rozbalí zip soubor a přečte CSV
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        with z.open('top-1m.csv') as f:
            reader = csv.reader(io.TextIOWrapper(f, 'utf-8'))
            seeds = ['https://' + row[1].strip() for i, row in enumerate(reader) if i < n]
    print(f"Načteno {len(seeds)} seed-URL.")
    return seeds

def create_table():
    """Vytváří tabulku v SQLite databázi, pokud ještě neexistuje."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS pages (
            id INTEGER PRIMARY KEY,
            url TEXT UNIQUE,
            title TEXT,
            content TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_page(url, title, content):
    """Ukládá stránku do databáze."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO pages (url, title, content) VALUES (?, ?, ?)',
              (url, title, content))
    conn.commit()
    conn.close()

def log_error(url, error_message):
    """Loguje chyby do souboru."""
    with open("chyby.log", "a", encoding="utf-8") as f:
        f.write(f"{url} → {error_message}\n")

def crawl(max_pages=20000000):
    """Funkce pro crawlování stránek."""
    # 1) vytvoř tabulku, než z ní budeš číst
    create_table()

    # 2) načti už uložené URL, abys je nepřetahoval znovu
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT url FROM pages")
    visited = set(r[0] for r in c.fetchall())
    conn.close()

    # 3) stáhni aktuální top-domény z Umbrella
    SEED_URLS = fetch_top_domains(n=20000)

    to_visit = [u for u in SEED_URLS if u not in visited]
    pages_crawled = 0

    try:
        while to_visit and pages_crawled < max_pages:
            if os.path.exists('STOP'):
                print("Detekován STOP soubor → ukončuji crawl.")
                break

            url = to_visit.pop(0)
            if url in visited:
                continue

            # Ignorujeme domény, které máme na seznamu
            if any(ignored in url for ignored in IGNORE_DOMAINS):
                print(f"Ignorováno: {url}")
                continue

            print(f"Crawling ({pages_crawled}/{max_pages}): {url}")
            retry_count = 0

            # Pokusíme se připojit, dokud nebude úspěšně načteno nebo nevyčerpáme pokusy
            while retry_count < MAX_RETRIES:
                try:
                    headers = {'User-Agent': 'Mozilla/5.0 (compatible; MyCrawler/1.0)'}
                    resp = requests.get(url, timeout=5, verify=False, headers=headers)

                    # Zpracování HTML a uložení
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    title = soup.title.string if soup.title else "No Title"
                    text = soup.get_text(separator=' ', strip=True)

                    save_page(url, title, text)
                    visited.add(url)
                    pages_crawled += 1

                    # Získání odkazů na další stránky
                    for link in soup.find_all('a', href=True):
                        full = urljoin(url, link['href'])
                        if urlparse(full).netloc and full not in visited:
                            to_visit.append(full)

                    break  # Připojení bylo úspěšné, takže přerušíme retry smyčku

                except (socket.gaierror, ConnectionError) as e:
                    error_message = f"Chyba připojení/DNS: {e}"
                    print(f"Chyba při crawl {url}: {error_message}")
                    log_error(url, error_message)
                    retry_count += 1

                except SSLError as e:
                    error_message = f"SSL chyba: {e}"
                    print(f"Chyba při crawl {url}: {error_message}")
                    log_error(url, error_message)
                    retry_count += 1

                except Timeout:
                    error_message = f"Timeout při crawl {url}"
                    print(f"Chyba při crawl {url}: {error_message}")
                    log_error(url, error_message)
                    retry_count += 1

                except RequestException as e:
                    error_message = f"Obecná chyba při požadavku: {e}"
                    print(f"Chyba při crawl {url}: {error_message}")
                    log_error(url, error_message)
                    retry_count += 1

                if retry_count < MAX_RETRIES:
                    print(f"Zkouším to znovu ({retry_count}/{MAX_RETRIES})...")
                    time.sleep(RETRY_DELAY)

            if retry_count == MAX_RETRIES:
                print(f"Počet pokusů vyčerpán pro {url}.")

    except KeyboardInterrupt:
        print("\nCrawler přerušen uživatelem (Ctrl+C).")

    finally:
        print(f"Hotovo – uloženo {pages_crawled} nových stránek.")

if __name__ == "__main__":
    crawl()
