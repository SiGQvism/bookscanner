import os
from fastapi import FastAPI, Request, Header
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Template
from dotenv import load_dotenv
from notion_client import Client
from .isbn import fetch_book

load_dotenv()
app = FastAPI()

# 📁 静的ファイルとテンプレートのマウント
app.mount("/static", StaticFiles(directory="static"), name="static")

# 📄 PWA対応ファイル
@app.get("/manifest.json")
def manifest():
    return FileResponse("static/manifest.json")

@app.get("/service-worker.js")
def service_worker():
    return FileResponse("static/service-worker.js")

# 📄 HTML画面表示
@app.get("/login", response_class=HTMLResponse)
def login_page():
    with open("templates/login.html", encoding="utf-8") as f:
        return Template(f.read()).render()

@app.get("/scan", response_class=HTMLResponse)
def scan_page():
    with open("templates/scan.html", encoding="utf-8") as f:
        return Template(f.read()).render()

# 📚 書籍登録API
@app.get("/add/{isbn}")
async def add_book(
    isbn: str,
    authorization: str = Header(...),
    x_database_id: str = Header(...)
):
    try:
        token = authorization.replace("Bearer ", "")
        dbid = x_database_id
        notion = Client(auth=token)

        data = fetch_book(isbn)

        # 🔍 既存チェック
        existing = notion.databases.query(
            **{
                "database_id": dbid,
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
                create_page(notion, dbid, data)
            except Exception as ne:
                return JSONResponse({"status": "NG", "message": f"Notion登録エラー: {ne}"})

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
        return JSONResponse({"status": "NG", "message": str(e)})

# ✅ Notionページ作成
def create_page(notion, dbid, b):
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
        parent={"database_id": dbid},
        properties=props
    )
