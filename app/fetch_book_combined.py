
import os
import requests
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO
import cloudinary
import cloudinary.uploader

# 環境変数の読み込みとCloudinary設定
load_dotenv()
cloudinary.config(cloudinary_url=os.getenv("CLOUDINARY_URL"))
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
RAKUTEN_APP_ID = os.getenv("RAKUTEN_APP_ID")

# Cloudinaryへのアップロード処理
def upload_to_cloudinary(image_bytes, public_id="book_cover"):
    try:
        result = cloudinary.uploader.upload(
            image_bytes,
            public_id=public_id,
            folder="bookscanner",
            overwrite=True,
            resource_type="image",
            format="jpg"
        )
        return result["secure_url"]
    except Exception as e:
        print("❌ Cloudinary upload error:", e)
        return ""

# 画像取得→検証→Cloudinaryアップロード
def convert_and_upload_image(url, isbn):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200 and "image" in response.headers.get("Content-Type", ""):
            img = Image.open(BytesIO(response.content)).convert("RGB")
            # 「image not available」か確認（幅・高さが極端に小さい場合）
            if img.size[0] < 100 or img.size[1] < 100:
                print("⚠️ 画像が小さすぎる可能性あり（プレースホルダー）:", url)
                return ""
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=90)
            buffer.seek(0)
            return upload_to_cloudinary(buffer, public_id=isbn)
    except Exception as e:
        print("❌ 画像変換エラー:", e)
    return ""

# 書籍情報統合関数
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

    # OpenBD
    try:
        res = requests.get(f"https://api.openbd.jp/v1/get?isbn={isbn}")
        if res.status_code == 200 and res.json()[0]:
            ob_data = res.json()[0]
            summary = ob_data.get("summary", {})
            result["title"] = summary.get("title", "") or result["title"]
            result["author"] = summary.get("author", "") or result["author"]
            result["publisher"] = summary.get("publisher", "") or result["publisher"]
            result["pub_date"] = summary.get("pubdate", "") or result["pub_date"]
            result["cover"] = summary.get("cover", "") or result["cover"]

            extents = ob_data.get("onix", {}).get("DescriptiveDetail", {}).get("Extent", [])
            if isinstance(extents, dict): extents = [extents]
            for ext in extents:
                if ext.get("ExtentUnit") == "03":
                    result["pages"] = ext.get("ExtentValue", "")
                    break

            prices = ob_data.get("onix", {}).get("ProductSupply", {}).get("SupplyDetail", {}).get("Price", [])
            if isinstance(prices, dict): prices = [prices]
            for price in prices:
                amount = price.get("PriceAmount")
                if amount:
                    result["price"] = amount
                    break
    except Exception as e:
        print(f"❌ OpenBDエラー: {e}")

    # Google Books
    try:
        google_url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}&key={GOOGLE_API_KEY}"
        res = requests.get(google_url)
        if res.status_code == 200:
            g_data = res.json()
            if g_data["totalItems"] > 0:
                item = g_data["items"][0]["volumeInfo"]
                url = item.get("imageLinks", {}).get("thumbnail", "")
                if url:
                    url = url.replace("&zoom=1", "&zoom=0").replace("&zoom=2", "&zoom=0") + "&fife=w800"
                    result["cover"] = url

                def update_if_empty(key, new_value):
                    if not result[key] or result[key].strip() == "" or result[key] == "情報なし":
                        result[key] = new_value

                update_if_empty("title", item.get("title", ""))
                update_if_empty("author", ", ".join(item.get("authors", [])))
                update_if_empty("publisher", item.get("publisher", ""))
                update_if_empty("pub_date", item.get("publishedDate", "").replace("-", ""))
                update_if_empty("summary", item.get("description", ""))
                update_if_empty("pages", str(item.get("pageCount", "")))
    except Exception as e:
        print(f"❌ Google Booksエラー: {e}")

    # Cloudinary アップロード
    try:
        if result["cover"]:
            print("🌐 Cloudinaryアップロード前URL:", result["cover"])
            cloudinary_url = convert_and_upload_image(result["cover"], isbn)
            print("🔁 Cloudinaryアップロード結果:", cloudinary_url)
            if cloudinary_url:
                result["cover"] = cloudinary_url
            else:
                raise Exception("Cloudinary upload failed")
    except Exception as e:
        print(f"⚠️ Cloudinary変換失敗: {e}")
        fallback = f"https://cover.openbd.jp/{isbn}.jpg"
        print(f"🆘 FallbackとしてOpenBD画像を使用: {fallback}")
        result["cover"] = fallback

    if not result["title"] and not result["author"]:
        raise Exception("書籍情報が見つかりませんでした")

    return result
