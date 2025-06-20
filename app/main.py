import os
from fastapi import FastAPI, Header, Body
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Template
from dotenv import load_dotenv
from notion_client import Client
from .fetch_book_combined import fetch_book_combined as fetch_book  # 相対パスに注意
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request

# ===============================
# 📦 環境設定・初期化
# ===============================
load_dotenv()
app = FastAPI()

# === パス定義 ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# === 静的ファイル提供（PWA対応） ===
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory="app/templates")

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/manifest.json")
def manifest():
    return FileResponse(os.path.join(STATIC_DIR, "manifest.json"))

@app.get("/service-worker.js")
def service_worker():
    return FileResponse(os.path.join(STATIC_DIR, "service-worker.js"))

# ===============================
# 🧑‍💻 フロントページ
# ===============================
@app.get("/", response_class=HTMLResponse)
def login_page():
    with open(os.path.join(TEMPLATE_DIR, "login.html"), encoding="utf-8") as f:
        return Template(f.read()).render()

@app.get("/scan", response_class=HTMLResponse)
def scan_page():
    with open(os.path.join(TEMPLATE_DIR, "scan.html"), encoding="utf-8") as f:
        return Template(f.read()).render()

# ===============================
# 📚 書籍追加エンドポイント
# ===============================
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

        # 重複チェック（ISBN）
        existing = notion.databases.query(
            database_id=db,
            filter={"property": "ISBN", "rich_text": {"equals": data["isbn"]}}
        )

        if not existing["results"]:
            create_page(notion, db, data)

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

# ===============================
# ✍️ 書評更新
# ===============================
@app.post("/review/{isbn}")
def add_review(
    isbn: str,
    body: dict = Body(...),
    authorization: str = Header(None),
    x_database_id: str = Header(None)
):
    try:
        token = authorization.replace("Bearer ", "")
        notion = Client(auth=token)
        db = x_database_id
        review_text = body.get("review", "")

        results = notion.databases.query(
            database_id=db,
            filter={"property": "ISBN", "rich_text": {"equals": isbn}}
        )

        if not results["results"]:
            return {"status": "NG", "message": "該当書籍が見つかりません"}

        page_id = results["results"][0]["id"]

        notion.pages.update(
            page_id=page_id,
            properties={"書評": {"rich_text": [{"text": {"content": review_text}}]}}
        )

        return {"status": "OK"}

    except Exception as e:
        return {"status": "NG", "message": str(e)}

# ===============================
# 🧱 Notion ページ作成関数
# ===============================
def create_page(notion, db, b):
    props = {
        "タイトル": {"title": [{"text": {"content": b["title"]}}]},
        "著者": {"rich_text": [{"text": {"content": b["author"]}}]},
        "ISBN": {"rich_text": [{"text": {"content": b["isbn"]}}]},
        "出版社": {"rich_text": [{"text": {"content": b["publisher"]}}]},
        "値段": {"number": int(b["price"])} if str(b["price"]).isdigit() else {"number": None},
        "出版日": {
            "date": {
                "start": f"{b['pub_date'][:4]}-{b['pub_date'][4:6]}-01"
            }
        } if len(b["pub_date"]) >= 6 else {"date": None},
        "ページ数": {"number": int(b["pages"])} if str(b["pages"]).isdigit() else {"number": None},
        "要約": {"rich_text": [{"text": {"content": b["summary"]}}]},
    }

    if b.get("cover"):
        props["画像"] = {
            "files": [{
                "name": "cover.jpg",
                "external": {"url": b["cover"]}
            }]
        }

    if b.get("review"):
        props["書評"] = {"rich_text": [{"text": {"content": b["review"]}}]}

    notion.pages.create(
        parent={"database_id": db},
        properties=props
    )
