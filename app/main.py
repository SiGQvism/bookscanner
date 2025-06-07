# main.py
import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
from notion_client import Client
from .isbn import fetch_book
from jinja2 import Template

load_dotenv()
app = FastAPI()

notion = Client(auth=os.getenv("NOTION_TOKEN"))
DB = os.getenv("NOTION_DB")

# --- ルート：カメラページ表示 ---
@app.get("/", response_class=HTMLResponse)
def camera_page():
    with open("templates/index.html", encoding="utf-8") as f:
        return Template(f.read()).render()

# --- ISBNスキャン時の処理 ---
# --- ISBNスキャン → 書籍情報返却 ---
@app.get("/add/{isbn}")
def add_book(isbn: str):
    try:
        data = fetch_book(isbn)

        # 🔍 既存登録チェック
        existing = notion.databases.query(
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
        if not existing["results"]:  # もし未登録なら
            try:
                create_page(data)
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


# --- Notionへの登録処理 ---
def create_page(b):
    props = {
        "タイトル": {"title": [{"text": {"content": b["title"]}}]},
        "著者":    {"rich_text": [{"text": {"content": b["author"]}}]},
        "ISBN":    {"rich_text": [{"text": {"content": b["isbn"]}}]},
        "値段":    {"number": int(b["price"])} if b["price"].isdigit() else {"number": None},
        "出版日":  {"date": {"start": f"{b['pub_date'][:4]}-{b['pub_date'][4:6]}-01"}} if b["pub_date"] else {"date": None},
        "ページ数": {"number": int(b["pages"])} if b["pages"].isdigit() else {"number": None},
        "要約":    {"rich_text": [{"text": {"content": b["summary"]}}]},
    }

    # ✅ 画像URLがあれば「画像」プロパティに追加
    if b.get("cover"):
        props["画像"] = {"files": [{"name": "cover.jpg", "external": {"url": b["cover"]}}]}

    notion.pages.create(
        parent={"database_id": DB},
        properties=props
    )
