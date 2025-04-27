from flask import Flask, request, render_template, jsonify, send_from_directory, redirect
from flask_apscheduler import APScheduler
from database import search_pages, suggest_terms, get_statistics
from crawler import crawl, fetch_top_domains
import os, random

class Config:
    SCHEDULER_API_ENABLED = True
    SCHEDULER_JOB_DEFAULTS = {'coalesce': False, 'max_instances': 1}

app = Flask(__name__)
app.config.from_object(Config())
app._static_folder = os.path.join(os.path.dirname(__file__), 'static')

# Scheduler: crawl každých 5 minut
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()
@scheduler.task('interval', id='crawl_job', minutes=1, misfire_grace_time=60)
def scheduled_crawl():
    crawl(max_pages=500)

def make_snippet(content, keyword, length=200):
    idx = content.lower().find(keyword.lower())
    if idx == -1:
        return content[:length] + ('...' if len(content)>length else '')
    start = max(0, idx-length//2)
    end = min(len(content), idx+length//2)
    snippet = content[start:end]
    return snippet.replace(keyword, f"<mark>{keyword}</mark>")

@app.route('/', methods=['GET'])
def home():
    query = request.args.get('q', '').strip()
    page = int(request.args.get('page', 1))
    per_page = 10
    results = []
    total_results = 0
    registered_pages, registered_cards = get_statistics()

    if query:
        allr = search_pages(query)
        total_results = len(allr)
        start, end = (page-1) * per_page, (page-1) * per_page + per_page
        for url, title, content in allr[start:end]:
            results.append({'url': url, 'title': title, 'snippet': make_snippet(content, query)})

    return render_template('search.html',
                           query=query,
                           results=results,
                           page=page,
                           per_page=per_page,
                           total_results=total_results,
                           total=registered_pages,   # <<< TADY přidávám 'total'
                           registered_pages=registered_pages,
                           registered_cards=registered_cards)

@app.route('/suggest', methods=['GET'])
def suggest():
    prefix = request.args.get('q','').strip()
    return jsonify(suggest_terms(prefix, limit=10) if prefix else [])

@app.route('/lucky', methods=['GET'])
def lucky():
    q = request.args.get('q','').strip()
    # pokud je dotaz, vrať první výsledek
    if q:
        res = search_pages(q)
        if res:
            return redirect(res[0][0])
        else:
            return redirect('/')
    # pokud žádný dotaz, přesměruj na náhodnou novou seed doménu
    seeds = fetch_top_domains(n=100)
    return redirect(random.choice(seeds))

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(app._static_folder, filename)

if __name__=="__main__":
    # port vezme Railway z env var PORT
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
