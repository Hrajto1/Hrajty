from fastapi import FastAPI
from crawler import crawl

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "online"}

@app.get("/crawl")
def run_crawler():
    crawl()
    return {"message": "Crawler spuštěn"}
