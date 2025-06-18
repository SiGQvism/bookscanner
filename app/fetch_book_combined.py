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

# 画像取得→検証→Cloudinaryアップロード（小さすぎる画像は除外）
def convert_and_upload_image(url, isbn):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200 and "image" in response.headers.get("Content-Type", ""):
            img = Image.open(BytesIO(response.content)).convert("RGB")

            # ✅ プレースホルダー画像対策：画像が小さければ除外
            if img.width < 200 or img.height < 200:
                print("⚠️ プレースホルダー画像と判定されたため除外:", url)
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

    # 1. OpenBD
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

    # 2. Google Books（補完）
    try:
        g_url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}&key={GOOGLE_API_KEY}"
        res = requests.get(g_url)
        if res.status_code == 200:
            g_data = res.json()
            if g_data["totalItems"] > 0:
                item = g_data["items"][0]["volumeInfo"]
                url = item.get("imageLinks", {}).get("thumbnail", "")
                if url:
                    url = url.replace("&zoom=1", "&zoom=0").replace("&zoom=2", "&zoom=0") + "&fife=w800"
                    result["cover"] = url

                def update_if_empty(key, new_value):
                    if not result[key]:
                        result[key] = new_value

                update_if_empty("title", item.get("title", ""))
                update_if_empty("author", ", ".join(item.get("authors", [])))
                update_if_empty("publisher", item.get("publisher", ""))
                update_if_empty("pub_date", item.get("publishedDate", "").replace("-", ""))
                update_if_empty("summary", item.get("description", ""))
                update_if_empty("pages", str(item.get("pageCount", "")))
    except Exception as e:
        print(f"❌ Google Booksエラー: {e}")

    # 3. 楽天ブックス（補完）
    try:
        r_url = f"https://app.rakuten.co.jp/services/api/BooksTotal/Search/20170404?format=json&isbn={isbn}&applicationId={RAKUTEN_APP_ID}"
        res = requests.get(r_url)
        if res.status_code == 200:
            items = res.json().get("Items", [])
            if items:
                item = items[0].get("Item", {})

                def update_if_empty(key, new_value):
                    if not result[key]:
                        result[key] = new_value

                update_if_empty("title", item.get("title", ""))
                update_if_empty("author", item.get("author", ""))
                update_if_empty("publisher", item.get("publisherName", ""))
                update_if_empty("price", str(item.get("itemPrice", "")))
                update_if_empty("pub_date", item.get("salesDate", "").replace("年", "").replace("月", "").replace("日", ""))
                update_if_empty("cover", item.get("largeImageUrl", ""))
    except Exception as e:
        print(f"❌ 楽天ブックスエラー: {e}")

    # ✅ Cloudinaryアップロード
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
        result["cover"] = f"https://cover.openbd.jp/{isbn}.jpg"

    # ✅ 最低限の情報がない場合はエラー
    if not result["title"] and not result["author"]:
        raise Exception("書籍情報が見つかりませんでした")

    return result
