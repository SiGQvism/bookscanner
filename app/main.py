import os
from fastapi import FastAPI, Request, Header
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from notion_client import Client
from .fetch_book_combined import fetch_book_combined as fetch_book

# .env読み込み
load_dotenv()

# FastAPI & テンプレートエンジン設定
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/manifest.json")
def manifest():
    return FileResponse("static/manifest.json")

@app.get("/service-worker.js")
def service_worker():
    return FileResponse("static/service-worker.js")

@app.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/scan", response_class=HTMLResponse)
def scan_page(request: Request):
    return templates.TemplateResponse("scan.html", {"request": request})

@app.get("/add/{isbn}")
def add_book(
    isbn: str,
    authorization: str = Header(None),
    x_database_id: str = Header(None)
):
    try:
        token = authorization.replace("Bearer ", "") if authorization else os.getenv("NOTION_TOKEN")
        db = x_database_id or os.getenv("NOTION_DATABASE_ID")

        if not token or not db:
            return JSONResponse(status_code=400, content={"status": "NG", "message": "NotionトークンまたはDB IDが不足"})

        notion = Client(auth=token)
        data = fetch_book(isbn)

        # すでに登録されているかチェック
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
                return JSONResponse(status_code=500, content={"status": "NG", "message": f"Notion登録エラー: {ne}"})
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
        return JSONResponse(status_code=500, content={"status": "NG", "message": str(e)})

def create_page(notion, db, b):
    props = {
        "タイトル": {"title": [{"text": {"content": b["title"]}}]},
        "著者": {"rich_text": [{"text": {"content": b["author"]}}]},
        "ISBN": {"rich_text": [{"text": {"content": b["isbn"]}}]},
        "値段": {"number": int(b["price"])} if b["price"].isdigit() else {"number": None},
        "出版日": {
            "date": {"start": f"{b['pub_date'][:4]}-{b['pub_date'][4:6]}-01"}
        } if b["pub_date"] else {"date": None},
        "ページ数": {"number": int(b["pages"])} if b["pages"].isdigit() else {"number": None},
        "要約": {"rich_text": [{"text": {"content": b["summary"][:1000]}}]}  # 長すぎる要約を制限
    }

    if b.get("cover"):
        props["画像"] = {
            "files": [{
                "name": "cover.jpg",
                "external": {"url": b["cover"]}
            }]
        }

    notion.pages.create(
        parent={"database_id": db},
        properties=props
    )
