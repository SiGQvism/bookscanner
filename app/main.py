import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from jinja2 import Template
from notion_client import Client
from .isbn import fetch_book

load_dotenv()

app = FastAPI()

# グローバルのDB ID（共通）
DB = os.getenv("NOTION_DB")

# 静的ファイル（CSSやJSなど）のマウント
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- PWA関連ルート ---
@app.get("/manifest.json")
def manifest():
    return FileResponse("static/manifest.json")

@app.get("/service-worker.js")
def service_worker():
    return FileResponse("static/service-worker.js")

# --- トップページ（Notionトークン入力画面） ---
@app.get("/", response_class=HTMLResponse)
def index():
    with open("templates/index.html", encoding="utf-8") as f:
        return Template(f.read()).render()

# --- スキャン用ページ（カメラ + ISBN登録） ---
@app.get("/scan", response_class=HTMLResponse)
def scan():
    with open("templates/scan.html", encoding="utf-8") as f:
        return Template(f.read()).render()

# --- 書籍登録API（Notionに登録） ---
@app.get("/add/{isbn}")
async def add_book(isbn: str, request: Request):
    try:
        token = request.headers.get("Authorization")
        if not token:
            return {"status": "NG", "message": "🔐 Notionトークンがありません"}

        user_notion = Client(auth=token)
        data = fetch_book(isbn)

        # --- 重複チェック ---
        existing = user_notion.databases.query(
            **{
                "database_id": DB,
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
                create_page(data, user_notion)
            except Exception as ne:
                print(f"Notion登録エラー: {ne}")
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


# --- Notion登録処理 ---
def create_page(b, notion_client):
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
        props["画像"] = {"files": [{"name": "cover.jpg", "external": {"url": b["cover"]}}]}

    notion_client.pages.create(
        parent={"database_id": DB},
        properties=props
    )
