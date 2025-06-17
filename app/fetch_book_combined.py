import os
import requests
from io import BytesIO
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader

# 環境変数読み込み
load_dotenv()

# Cloudinary設定
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
RAKUTEN_APP_ID = os.getenv("RAKUTEN_APP_ID")

def fetch_rakuten_books(isbn):
    try:
        url = (
            f"https://app.rakuten.co.jp/services/api/BooksBook/Search/20170404"
            f"?format=json&isbn={isbn}&booksGenreId=001004008&applicationId={RAKUTEN_APP_ID}"
        )
        res = requests.get(url)
        res.raise_for_status()
        item = res.json()["Items"][0]["Item"]
        return {
            "title": item.get("title", ""),
            "author": item.get("author", ""),
            "publisher": item.get("publisherName", ""),
            "pub_date": item.get("salesDate", "").replace("年", "").replace("月", "").replace("日", ""),
            "price": str(item.get("itemPrice", "")),
            "cover": item.get("largeImageUrl", "")
        }
    except Exception as e:
        print("📕 RakutenBooks error:", e)
        return {}

def fetch_openbd(isbn):
    try:
        res = requests.get(f"https://api.openbd.jp/v1/get?isbn={isbn}")
        item = res.json()[0]
        if not item:
            return {}
        summary = item["summary"]
        return {
            "title": summary.get("title", ""),
            "author": summary.get("author", ""),
            "publisher": summary.get("publisher", ""),
            "pub_date": summary.get("pubdate", ""),
            "cover": summary.get("cover", "")
        }
    except Exception as e:
        print("📘 OpenBD error:", e)
        return {}

def fetch_google_books(isbn):
    try:
        url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}&key={GOOGLE_API_KEY}"
        res = requests.get(url)
        item = res.json()["items"][0]["volumeInfo"]
        return {
            "title": item.get("title", ""),
            "author": ", ".join(item.get("authors", [])),
            "publisher": item.get("publisher", ""),
            "pub_date": item.get("publishedDate", "").replace("-", ""),
            "summary": item.get("description", ""),
            "pages": str(item.get("pageCount", "")),
            "cover": item.get("imageLinks", {}).get("thumbnail", "").replace("http://", "https://")
        }
    except Exception as e:
        print("📗 GoogleBooks error:", e)
        return {}

def upload_cover_to_cloudinary(url, isbn):
    try:
        if not url or "notavailable" in url:
            return ""
        response = requests.get(url)
        if response.status_code != 200:
            return ""
        img = BytesIO(response.content)
        result = cloudinary.uploader.upload(img, public_id=f"bookcovers/{isbn}", overwrite=True)
        return result["secure_url"]
    except Exception as e:
        print("🌩️ Cloudinary error:", e)
        return ""

def fetch_book_combined(isbn: str) -> dict:
    result = {"isbn": isbn}

    # 優先順位：楽天 → OpenBD → Google Books
    for source in [fetch_rakuten_books, fetch_openbd, fetch_google_books]:
        data = source(isbn)
        for k, v in data.items():
            if k not in result or not result[k]:
                result[k] = v

    # 画像アップロード（Cloudinaryに保存）
    result["cover"] = upload_cover_to_cloudinary(result.get("cover", ""), isbn)

    return result
