from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from notion_client import Client
from app.fetch_book_combined import fetch_book_combined
import os

app = FastAPI()

# 静的ファイルとテンプレート
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# 📄 HTMLページのルーティング
@app.get("/", response_class=HTMLResponse)
async def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/scan", response_class=HTMLResponse)
async def scan(request: Request):
    return templates.TemplateResponse("scan.html", {"request": request})

# 📚 書籍情報取得（ISBN）
@app.get("/book")
async def get_book(isbn: str):
    try:
        result = fetch_book_combined(isbn)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(status_code=404, content={"error": str(e)})

# 📝 Notionへの登録エンドポイント
@app.post("/notion")
async def add_to_notion(
    isbn: str = Form(...),
    title: str = Form(...),
    author: str = Form(...),
    publisher: str = Form(...),
    pub_date: str = Form(...),
    pages: str = Form(...),
    price: str = Form(...),
    summary: str = Form(...),
    cover: str = Form(...),
    token: str = Form(...),
    database_id: str = Form(...)
):
    try:
        notion = Client(auth=token)
        notion.pages.create(
            parent={"database_id": database_id},
            properties={
                "書名": {"title": [{"text": {"content": title}}]},
                "著者": {"rich_text": [{"text": {"content": author}}]},
                "出版社": {"rich_text": [{"text": {"content": publisher}}]},
                "出版日": {"rich_text": [{"text": {"content": pub_date}}]},
                "ページ数": {"number": int(pages) if pages.isdigit() else None},
                "価格": {"rich_text": [{"text": {"content": price}}]},
                "ISBN": {"rich_text": [{"text": {"content": isbn}}]},
                "要約": {"rich_text": [{"text": {"content": summary}}]},
                "カバー画像": {
                    "files": [{
                        "name": "cover.jpg",
                        "external": {"url": cover}
                    }] if cover else []
                }
            }
        )
        return {"message": "登録完了"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
