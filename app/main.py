import os
from fastapi import FastAPI, Header, Body
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Template
from dotenv import load_dotenv
from notion_client import Client
from .fetch_book_combined import fetch_book_combined as fetch_book

load_dotenv()
app = FastAPI()

# 静的ファイルのマウント
app.mount("/static", StaticFiles(directory="static"), name="static")

# ======================
# PWA用マニフェストとSW
# ======================
@app.get("/manifest.json")
def manifest():
    return FileResponse("static/manifest.json")

@app.get("/service-worker.js")
def service_worker():
    return FileResponse("static/service-worker.js")

# ======================
# HTMLページルーティング
# ======================
@app.get("/", response_class=HTMLResponse)
def login_page():
    with open("templates/login.html", encoding="utf-8") as f:
        return Template(f.read()).render()

@app.get("/scan", response_class=HTMLResponse)
def scan_page():
    with open("templates/scan.html", encoding="utf-8") as f:
        return Template(f.read()).render()

# ======================
# 書籍情報取得＋Notion登録
# ======================
@app.post("/add/{isbn}")
def add_book(
    isbn: str,
    body: dict = Body(...),
    authorization: str = Header(None),
    x_database_id: str = Header(None)
):
    try:
        if not authorization or not x_database_id:
            return {"status": "NG", "message": "Missing Notion token or database ID"}

        token = authorization.replace("Bearer ", "")
        notion = Client(auth=token)
        db = x_database_id
        review = body.get("review", "")

        data = fetch_book(isbn)
        data["review"] = review

        # 重複チェック
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
            create_page(notion, db, data)
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

# ======================
# 書評を個別に登録・更新
# ======================
@app.post("/review/{isbn}")
def add_review(
    isbn: str,
    body: dict = Body(...),
    authorization: str = Header(None),
    x_database_id: str = Header(None)
):
    try:
        if not authorization or not x_database_id:
            return {"status": "NG", "message": "Missing Notion token or database ID"}

        token = authorization.replace("Bearer ", "")
        notion = Client(auth=token)
        db = x_database_id
        review_text = body.get("review", "")

        if not review_text:
            return {"status": "NG", "message": "書評が空です"}

        # ページ取得（ISBN一致）
        results = notion.databases.query(
            **{
                "database_id": db,
                "filter": {
                    "property": "ISBN",
                    "rich_text": {
                        "equals": isbn
                    }
                }
            }
        )

        if not results["results"]:
            return {"status": "NG", "message": "該当する書籍が見つかりません"}

        page_id = results["results"][0]["id"]

        # 書評を更新（プロパティ名：書評）
        notion.pages.update(
            page_id=page_id,
            properties={
                "書評": {
                    "rich_text": [{"text": {"content": review_text}}]
                }
            }
        )

        return {"status": "OK"}

    except Exception as e:
        return {"status": "NG", "message": str(e)}

# ======================
# Notionページ作成処理
# ======================
def create_page(notion, db, b):
    props = {
        "タイトル": {"title": [{"text": {"content": b["title"]}}]},
        "著者": {"rich_text": [{"text": {"content": b["author"]}}]},
        "ISBN": {"rich_text": [{"text": {"content": b["isbn"]}}]},
        "値段": {"number": int(b["price"])} if str(b["price"]).isdigit() else {"number": None},
        "出版日": {"date": {"start": f"{b['pub_date'][:4]}-{b['pub_date'][4:6]}-01"}} if b["pub_date"] else {"date": None},
        "ページ数": {"number": int(b["pages"])} if str(b["pages"]).isdigit() else {"number": None},
        "要約": {"rich_text": [{"text": {"content": b["summary"]}}]},
    }

    if b.get("cover"):
        props["画像"] = {"files": [{"name": "cover.jpg", "external": {"url": b["cover"]}}]}

    if b.get("review"):
        props["書評"] = {"rich_text": [{"text": {"content": b["review"]}}]}

    notion.pages.create(
        parent={"database_id": db},
        properties=props
    )
