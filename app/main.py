import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from jinja2 import Template
from .isbn import fetch_book
from notion_client import Client

load_dotenv()
app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

# CORS（開発中のブラウザ制限解除用、必要なら）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- PWA関連ファイル返却 ---
@app.get("/manifest.json")
def manifest():
    return FileResponse("static/manifest.json")


@app.get("/service-worker.js")
def service_worker():
    return FileResponse("static/service-worker.js")


@app.get("/favicon.ico")
def favicon():
    return FileResponse("static/isbn192.png")

# --- ルート（ログインフォーム） ---
@app.get("/", response_class=HTMLResponse)
def login_page():
    with open("templates/login.html", encoding="utf-8") as f:
        return HTMLResponse(f.read())


# --- スキャンページ ---
@app.get("/scan", response_class=HTMLResponse)
def scan_page():
    with open("templates/scan.html", encoding="utf-8") as f:
        return HTMLResponse(f.read())


# --- 書籍登録処理（POST） ---
@app.post("/add/{isbn}")
async def add_book(isbn: str, request: Request):
    try:
        body = await request.json()
        token = body.get("token")
        db_id = body.get("db_id")
        if not token or not db_id:
            return JSONResponse(content={"status": "NG", "message": "トークンまたはDB IDが不足しています"}, status_code=400)

        notion = Client(auth=token)
        data = fetch_book(isbn)

        # --- 既存チェック ---
        existing = notion.databases.query(
            **{
                "database_id": db_id,
                "filter": {
                    "property": "ISBN",
                    "rich_text": {
                        "equals": data["isbn"]
                    }
                }
            }
        )
        if not existing["results"]:
            # --- 新規作成 ---
            props = {
                "タイトル": {"title": [{"text": {"content": data["title"]}}]},
                "著者": {"rich_text": [{"text": {"content": data["author"]}}]},
                "ISBN": {"rich_text": [{"text": {"content": data["isbn"]}}]},
                "値段": {"number": int(data["price"])} if data["price"].isdigit() else {"number": None},
                "出版日": {"date": {"start": f"{data['pub_date'][:4]}-{data['pub_date'][4:6]}-01"}} if data["pub_date"] else {"date": None},
                "ページ数": {"number": int(data["pages"])} if data["pages"].isdigit() else {"number": None},
                "要約": {"rich_text": [{"text": {"content": data["summary"]}}]},
            }

            if data.get("cover"):
                props["画像"] = {"files": [{"name": "cover.jpg", "external": {"url": data["cover"]}}]}

            notion.pages.create(
                parent={"database_id": db_id},
                properties=props
            )

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
