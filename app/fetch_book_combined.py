import os
import requests
import cloudinary.uploader
from dotenv import load_dotenv

load_dotenv()

# 環境変数
RAKUTEN_APP_ID = os.getenv("RAKUTEN_APP_ID")
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET
)

def fetch_book_combined(isbn: str) -> dict:
    book = {
        "isbn": isbn,
        "title": "",
        "author": "",
        "publisher": "",
        "pub_date": "",
        "price": "",
        "pages": "",
        "summary": "",
        "cover": ""
    }

    # --- 1. Google Books ---
    try:
        gb_url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
        gb_res = requests.get(gb_url)
        gb_data = gb_res.json()
        info = gb_data["items"][0]["volumeInfo"]

        book["title"] = info.get("title", book["title"])
        book["author"] = ", ".join(info.get("authors", [])) or book["author"]
        book["summary"] = info.get("description", book["summary"])
        book["pages"] = str(info.get("pageCount", "")) or book["pages"]
        book["cover"] = info.get("imageLinks", {}).get("thumbnail", book["cover"])
    except Exception as e:
        print("Google Books error:", e)

    # --- 2. OpenBD ---
    try:
        ob_url = f"https://api.openbd.jp/v1/get?isbn={isbn}"
        ob_res = requests.get(ob_url).json()
        if ob_res[0]:
            summary = ob_res[0]["summary"]
            book["title"] = summary.get("title", book["title"])
            book["author"] = summary.get("author", book["author"])
            book["publisher"] = summary.get("publisher", book["publisher"])
            book["pub_date"] = summary.get("pubdate", book["pub_date"])
            book["price"] = summary.get("price", book["price"])
            book["cover"] = summary.get("cover", book["cover"])
    except Exception as e:
        print("OpenBD error:", e)

    # --- 3. 楽天ブックスAPI ---
    try:
        if RAKUTEN_APP_ID:
            rk_url = (
                f"https://app.rakuten.co.jp/services/api/BooksBook/Search/20170404"
                f"?format=json&isbn={isbn}&applicationId={RAKUTEN_APP_ID}"
            )
            rk_res = requests.get(rk_url)
            rk_res.raise_for_status()
            rk_json = rk_res.json()
            if rk_json["Items"]:
                item = rk_json["Items"][0]["Item"]
                book["title"] = item.get("title", book["title"])
                book["author"] = item.get("author", book["author"])
                book["publisher"] = item.get("publisherName", book["publisher"])
                book["pub_date"] = item.get("salesDate", book["pub_date"])
                book["price"] = str(item.get("itemPrice", book["price"]))
                book["cover"] = item.get("largeImageUrl", book["cover"])
    except Exception as e:
        print("RakutenBooks error:", e)

    # --- 4. Cloudinaryへアップロード（Google画像があっても） ---
    try:
        if book["cover"]:
            upload_res = cloudinary.uploader.upload(
                book["cover"],
                folder="bookcovers",
                public_id=isbn,
                overwrite=True,
                timeout=10
            )
            book["cover"] = upload_res.get("secure_url", book["cover"])
    except Exception as e:
        print("Cloudinary upload error:", e)

    return book
