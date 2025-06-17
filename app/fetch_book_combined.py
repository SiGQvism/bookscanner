import os
import requests
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

def fetch_book_combined(isbn: str) -> dict:
    print(f"📘 Fetching book info for ISBN: {isbn}")

    # Google Books APIから基本情報取得
    gb_url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
    gb_res = requests.get(gb_url)
    gb_data = gb_res.json()

    if "items" not in gb_data:
        raise ValueError(f"📕 Google Booksに該当なし: ISBN {isbn}")

    info = gb_data["items"][0]["volumeInfo"]

    title = info.get("title", "")
    authors = info.get("authors", [""])  # リスト対応
    author = ", ".join(authors)
    publisher = info.get("publisher", "")
    pub_date = info.get("publishedDate", "").replace("-", "")  # 例: 2020-01 → 202001
    summary = info.get("description", "").replace("\n", " ").strip()
    page_count = info.get("pageCount", "")
    price = ""  # Google Booksから価格は取得不可

    # カバー画像取得（安全な方法）
    image_url = ""
    image_links = info.get("imageLinks", {})
    for key in ["extraLarge", "large", "medium", "small", "thumbnail", "smallThumbnail"]:
        url = image_links.get(key, "")
        if url and is_valid_image_url(url):
            image_url = url
            break

    # Cloudinaryへアップロード（画像が存在する場合のみ）
    cover = ""
    if image_url:
        try:
            upload_result = cloudinary.uploader.upload(image_url, public_id=f"bookscanner/{isbn}")
            cover = upload_result.get("secure_url", "")
        except Exception as e:
            print(f"⚠️ Cloudinary upload failed: {e}")

    return {
        "title": title,
        "author": author,
        "publisher": publisher,
        "pub_date": pub_date,
        "summary": summary,
        "pages": page_count,
        "price": price,
        "cover": cover,
        "isbn": isbn
    }

def is_valid_image_url(url: str) -> bool:
    """HEADリクエストで画像が存在するか確認"""
    try:
        r = requests.head(url, timeout=5)
        return r.status_code == 200
    except:
        return False
