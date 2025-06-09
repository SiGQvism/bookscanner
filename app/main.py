import os
from fastapi import FastAPI, Request, Header
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Template
from dotenv import load_dotenv
from notion_client import Client
from isbn import fetch_book

load_dotenv()
app = FastAPI()

# Static file mount
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/manifest.json")
def manifest():
    return FileResponse("static/manifest.json")

@app.get("/service-worker.js")
def service_worker():
    return FileResponse("static/service-worker.js")

# HTML page routing
@app.get("/", response_class=HTMLResponse)
def login_page():
    with open("templates/login.html", encoding="utf-8") as f:
        return Template(f.read()).render()

@app.get("/scan", response_class=HTMLResponse)
def scan_page():
    with open("templates/scan.html", encoding="utf-8") as f:
        return Template(f.read()).render()

# API endpoint for adding book to Notion
@app.get("/add/{isbn}")
def add_book(isbn: str, authorization: str = Header(None), x_database_id: str = Header(None)):
    try:
        if not authorization or not x_database_id:
            return {"status": "NG", "message": "Missing Notion token or database ID"}

        token = authorization.replace("Bearer ", "")
        notion = Client(auth=token)
        db = x_database_id

        data = fetch_book(isbn)

        # Check for existing record
        existing = notion.databases.query(
            **{
                "database_id": db,
                "filter": {
                    "property": "ISBN",
                    "rich_text": {
                        "equals": data["isbn"]
                    }
                }
            }
        )

        if not existing["results"]:
            try:
                create_page(notion, db, data)
            except Exception as ne:
                return {"status": "NG", "message": f"Notion登録エラー: {ne}"}
        else:
            print(f"⚠️ 既に登録済み: ISBN {data['isbn']}")

        return {
            "status": "OK",
            "title": data["title"],
            "author": data["author"],
            "publisher": data["publisher"],
            "pub_date": data["pub_date"],
            "price": data["price"],
            "pages": data["pages"],
            "summary": data["summary"],
            "cover": data["cover"]
        }

    except Exception as e:
        return {"status": "NG", "message": str(e)}


def create_page(notion, db, b):
    props = {
        "タイトル": {"title": [{"text": {"content": b["title"]}}]},
        "著者": {"rich_text": [{"text": {"content": b["author"]}}]},
        "ISBN": {"rich_text": [{"text": {"content": b["isbn"]}}]},
        "値段": {"number": int(b["price"])} if b["price"].isdigit() else {"number": None},
        "出版日": {"date": {"start": f"{b['pub_date'][:4]}-{b['pub_date'][4:6]}-01"}} if b["pub_date"] else {"date": None},
        "ページ数": {"number": int(b["pages"])} if b["pages"].isdigit() else {"number": None},
        "要約": {"rich_text": [{"text": {"content": b["summary"]}}]},
    }

    if b.get("cover"):
        props["画像"] = {"files": [{"name": "cover.jpg", "external": {"url": b["cover"]}}]}

    notion.pages.create(
        parent={"database_id": db},
        properties=props
    )
