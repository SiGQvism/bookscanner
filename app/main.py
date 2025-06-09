
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from notion_client import Client
from jinja2 import Template
from isbn import fetch_book

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def login():
    with open("templates/login.html", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.get("/scan")
def scan():
    with open("templates/scan.html", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.get("/manifest.json")
def manifest():
    return FileResponse("static/manifest.json")

@app.get("/service-worker.js")
def sw():
    return FileResponse("static/service-worker.js")

@app.get("/add/{isbn}")
def add_book(isbn: str, token: str, db: str):
    notion = Client(auth=token)
    data = fetch_book(isbn)

    existing = notion.databases.query(
        **{
            "database_id": db,
            "filter": {
                "property": "ISBN",
                "rich_text": {"equals": data["isbn"]}
            }
        }
    )

    if not existing["results"]:
        props = {
            "タイトル": {"title": [{"text": {"content": data["title"]}}]},
            "著者": {"rich_text": [{"text": {"content": data["author"]}}]},
            "ISBN": {"rich_text": [{"text": {"content": data["isbn"]}}]},
            "要約": {"rich_text": [{"text": {"content": data["summary"]}}]}
        }
        if data.get("cover"):
            props["画像"] = {"files": [{"external": {"url": data["cover"]}}]}

        notion.pages.create(
            parent={"database_id": db},
            properties=props
        )

    return {
        "status": "OK",
        "title": data["title"],
        "author": data["author"],
        "publisher": data["publisher"],
        "summary": data["summary"],
        "cover": data["cover"]
    }