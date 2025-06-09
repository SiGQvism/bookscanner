import os
from fastapi import FastAPI, Request, Header
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Template
from notion_client import Client
from dotenv import load_dotenv
from .isbn import fetch_book

load_dotenv()
app = FastAPI()

# 静的ファイルのマウント
app.mount("/static", StaticFiles(directory="static"), name="static")

# 🔧 PWAリソース
@app.get("/manifest.json")
def manifest():
    return FileResponse("static/manifest.json")

@app.get("/service-worker.js")
def service_worker():
    return FileResponse("static/service-worker.js")


# --- 📄 ログインページ表示 ---
@app.get("/", response_class=HTMLResponse)
def login_page():
    with open("templates/login.html", encoding="utf-8") as f:
        return Template(f.read()).render()


# --- 📷 スキャンページ表示 ---
@app.get("/scan", response_class=HTMLResponse)
def scan_page():
    with open("templates/scan.html", encoding="utf-8") as f:
        return Template(f.read()).render()


# --- 📚 書籍情報取得＆Notion登録 ---
@app.post("/add/{isbn}")
async def add_book(
    isbn: str,
    authorization: str = Header(None),
    x_database_id: str = Header(None)
):
    try:
        token = authorization.replace("Bearer ", "")
        notion = Client(auth=token)
        DB = x_database_id

        # 書籍情報取得
        data = fetch_book(isbn)

        # 🔍 既存チェック
        existing = notion.databases.query(
            **{
                "database_id": DB,
                "filter": {
                    "property": "ISBN",
                    "rich_text": {"equals": data["isbn"]}
                }
            }
        )

        if not existing["results"]:
            try:
                create_page(notion, DB, data)
            except Exception as e:
                print(f"❌ Notion登録エラー: {e}")
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


# --- 📄 Notionページ登録 ---
def create_page(notion, DB, b):
    props = {
        "タイトル": {"title": [{"text": {"content": b["title"]}}]},
        "著者":    {"rich_text": [{"text": {"content": b["author"]}}]},
        "ISBN":    {"rich_text": [{"text": {"content": b["isbn"]}}]},
        "値段":    {"number": int(b["price"])} if b["price"].isdigit() else {"number": None},
        "出版日":  {"date": {"start": f"{b['pub_date'][:4]}-{b['pub_date'][4:6]}-01"}} if b["pub_date"] else {"date": None},
        "ページ数": {"number": int(b["pages"])} if b["pages"].isdigit() else {"number": None},
        "要約":    {"rich_text": [{"text": {"content": b["summary"]}}]},
    }

    if b.get("cover"):
        props["画像"] = {
            "files": [{"name": "cover.jpg", "external": {"url": b["cover"]}}]
        }

    notion.pages.create(
        parent={"database_id": DB},
        properties=props
    )
