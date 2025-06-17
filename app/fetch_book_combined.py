import os
import requests
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
RAKUTEN_APP_ID = os.getenv("RAKUTEN_APP_ID")


def upload_to_cloudinary(image_bytes, public_id):
    try:
        resp = cloudinary.uploader.upload(
            image_bytes,
            public_id=public_id,
            folder="bookscanner",
            overwrite=True,
            resource_type="image",
            format="jpg",
        )
        return resp["secure_url"]
    except Exception as e:
        print("❌ Cloudinary upload error:", e)
        return ""


def convert_and_upload_image(url, isbn):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        img = Image.open(BytesIO(r.content)).convert("RGB")
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=90)
        buf.seek(0)
        return upload_to_cloudinary(buf, public_id=isbn)
    except Exception as e:
        print("❌ Image conversion/upload error:", e)
        return ""


def fetch_book_combined(isbn: str) -> dict:
    result = {
        "isbn": isbn,
        "title": "",
        "author": "",
        "publisher": "",
        "pub_date": "",
        "pages": "",
        "price": "",
        "summary": "",
        "cover": ""
    }

    # 1. OpenBDデータ取得
    try:
        r = requests.get(f"https://api.openbd.jp/v1/get?isbn={isbn}", timeout=10)
        r.raise_for_status()
        ob = r.json()[0]
        if ob:
            s = ob.get("summary", {})
            result.update({
                k: s.get(k, result[k]) for k in ["title", "author", "publisher", "pubdate"]
            })
            result["cover"] = s.get("cover", result["cover"])

            # ONIXよりページ数
            ext = ob.get("onix", {}).get("DescriptiveDetail", {}).get("Extent", [])
            if isinstance(ext, dict):
                ext = [ext]
            for e in ext:
                if e.get("ExtentUnit") == "03":
                    result["pages"] = e.get("ExtentValue", "")

            # ONIXより価格
            prices = ob.get("onix", {}).get("ProductSupply", {}).get("SupplyDetail", {}).get("Price", [])
            if isinstance(prices, dict):
                prices = [prices]
            for p in prices:
                if p.get("PriceAmount"):
                    result["price"] = p["PriceAmount"]
                    break
    except Exception as e:
        print("❌ OpenBD error:", e)

    # 2. 楽天ブックス補完
    try:
        r = requests.get(
            "https://app.rakuten.co.jp/services/api/BooksBook/Search/20170404",
            params={"format": "json", "isbn": isbn, "applicationId": RAKUTEN_APP_ID},
            timeout=10
        )
        r.raise_for_status()
        items = r.json().get("Items") or []
        if items:
            rb = items[0]["Item"]
            fields = {
                "title": rb.get("title"),
                "author": rb.get("author"),
                "publisher": rb.get("publisherName"),
                "price": str(rb.get("itemPrice", "")),
                "summary": rb.get("itemCaption"),
                "cover": rb.get("largeImageUrl")
            }
            for k, v in fields.items():
                if not result.get(k) and v:
                    result[k] = v
    except Exception as e:
        print("❌ RakutenBooks error:", e)

    # 3. Google Books 補完
    try:
        r = requests.get(
            f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}",
            params={"key": GOOGLE_API_KEY},
            timeout=10
        )
        r.raise_for_status()
        items = r.json().get("items") or []
        if items:
            g = items[0]["volumeInfo"]
            fields = {
                "title": g.get("title"),
                "author": ", ".join(g.get("authors", [])),
                "publisher": g.get("publisher"),
                "pub_date": g.get("publishedDate", "").replace("-", ""),
                "pages": str(g.get("pageCount", "")),
                "summary": g.get("description")
            }
            for k, v in fields.items():
                if not result.get(k) and v:
                    result[k] = v

            # カバー画像
            if not result["cover"]:
                thumb = g.get("imageLinks", {}).get("thumbnail", "")
                if thumb:
                    result["cover"] = thumb.replace("&zoom=1", "&zoom=0").replace("&zoom=2", "&zoom=0") + "&fife=w800"
    except Exception as e:
        print("❌ GoogleBooks error:", e)

    # 4. Cloudinary アップロード
    if result["cover"]:
        print("🌐 Cloudinary upload source:", result["cover"])
        uploaded = convert_and_upload_image(result["cover"], isbn)
        if uploaded:
            result["cover"] = uploaded
        else:
            print("⚠️ Cloudinary upload failed, using OpenBD fallback")
            result["cover"] = f"https://cover.openbd.jp/{isbn}.jpg"

    # 最低限のチェック
    if not (result["title"] or result["author"]):
        raise Exception("書籍情報が取得できませんでした")

    return result
