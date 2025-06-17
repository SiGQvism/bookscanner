import os
import requests
import cloudinary
import cloudinary.uploader
from io import BytesIO
from fastapi import FastAPI, Header, Body
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Template
from dotenv import load_dotenv
from notion_client import Client
from app.fetch_book_combined import fetch_book_combined as fetch_book



load_dotenv()
app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/manifest.json")
def manifest():
    return FileResponse("static/manifest.json")

@app.get("/service-worker.js")
def service_worker():
    return FileResponse("static/service-worker.js")

@app.get("/", response_class=HTMLResponse)
def login_page():
    with open(os.path.join(TEMPLATE_DIR, "login.html"), encoding="utf-8") as f:
        return Template(f.read()).render()

@app.get("/scan", response_class=HTMLResponse)
def scan_page():
    with open(os.path.join(TEMPLATE_DIR, "scan.html"), encoding="utf-8") as f:
        return Template(f.read()).render()

@app.post("/add/{isbn}")
def add_book(isbn: str, body: dict = Body(...), authorization: str = Header(None), x_database_id: str = Header(None)):
    try:
        if not authorization or not x_database_id:
            return {"status": "NG", "message": "Missing Notion token or database ID"}

        token = authorization.replace("Bearer ", "")
        notion = Client(auth=token)
        db = x_database_id
        review = body.get("review", "")

        data = fetch_book(isbn)
        data["review"] = review

        existing = notion.databases.query(
            database_id=db,
            filter={"property": "ISBN", "rich_text": {"equals": data["isbn"]}}
        )

        if not existing["results"]:
            create_page(notion, db, data)
        else:
            print(f"⚠️ 既に登録済み: ISBN {data['isbn']}")

        print("✅ 最終データ:", data)

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

@app.post("/review/{isbn}")
def add_review(isbn: str, body: dict = Body(...), authorization: str = Header(None), x_database_id: str = Header(None)):
    try:
        if not authorization or not x_database_id:
            return {"status": "NG", "message": "Missing Notion token or database ID"}

        token = authorization.replace("Bearer ", "")
        notion = Client(auth=token)
        db = x_database_id
        review_text = body.get("review", "")

        if not review_text:
            return {"status": "NG", "message": "書評が空です"}

        results = notion.databases.query(
            database_id=db,
            filter={"property": "ISBN", "rich_text": {"equals": isbn}}
        )

        if not results["results"]:
            return {"status": "NG", "message": "該当する書籍が見つかりません"}

        page_id = results["results"][0]["id"]

        notion.pages.update(
            page_id=page_id,
            properties={"書評": {"rich_text": [{"text": {"content": review_text}}]}}
        )

        return {"status": "OK"}

    except Exception as e:
        return {"status": "NG", "message": str(e)}

def create_page(notion, db, b):
    props = {
        "タイトル": {"title": [{"text": {"content": b["title"]}}]},
        "著者": {"rich_text": [{"text": {"content": b["author"]}}]},
        "ISBN": {"rich_text": [{"text": {"content": b["isbn"]}}]},
        "値段": {"number": int(b["price"])} if str(b["price"]).isdigit() else {"number": None},
        "出版日": {"date": {"start": f"{b['pub_date'][:4]}-{b['pub_date'][4:6]}-01"}} if len(b["pub_date"]) >= 6 else {"date": None},
        "ページ数": {"number": int(b["pages"])} if str(b["pages"]).isdigit() else {"number": None},
        "要約": {"rich_text": [{"text": {"content": b["summary"]}}]},
    }

    if b.get("cover"):
        props["画像"] = {"files": [{"name": "cover.jpg", "external": {"url": b["cover"]}}]}

    if b.get("review"):
        props["書評"] = {"rich_text": [{"text": {"content": b["review"]}}]}

    notion.pages.create(parent={"database_id": db}, properties=props)
