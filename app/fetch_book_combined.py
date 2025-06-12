import os
import requests
from dotenv import load_dotenv

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TIMEOUT = (3.5, 5)   # (connect, read)

def _get_json(url):
    try:
        return requests.get(url, timeout=TIMEOUT).json()
    except requests.exceptions.RequestException as e:
        print("🔌 HTTP Error:", e)
        return None


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

    # ========== OpenBD API ==========
    openbd_url = f"https://api.openbd.jp/v1/get?isbn={isbn}"
    try:
        res = requests.get(openbd_url)
        if res.status_code == 200:
            ob_data = res.json()[0]
            if ob_data:
                summary = ob_data.get("summary", {})
                result["title"] = summary.get("title", "") or result["title"]
                result["author"] = summary.get("author", "") or result["author"]
                result["publisher"] = summary.get("publisher", "") or result["publisher"]
                result["pub_date"] = summary.get("pubdate", "") or result["pub_date"]
                result["summary"] = summary.get("volume") or summary.get("toc") or result["summary"]
                result["cover"] = summary.get("cover", "") or result["cover"]
                result["pages"]   = result["pages"] or summary.get("pages", "")

                # ページ数（Extent → ExtentUnit=03）
                extents = ob_data.get("onix", {}).get("DescriptiveDetail", {}).get("Extent", [])
                if isinstance(extents, dict):  # 単体辞書の場合もある
                    extents = [extents]
                for ext in extents:
                    if ext.get("ExtentUnit") == "03":
                        result["pages"] = result["pages"] or ext.get("ExtentValue", "")
                        break

                # 値段（PriceAmount）
                prices = ob_data.get("onix", {}).get("ProductSupply", {}).get("SupplyDetail", {}).get("Price", [])
                if isinstance(prices, dict):  # これも単体辞書の場合あり
                    prices = [prices]
                for price in prices:
                    amount = price.get("PriceAmount")
                    if amount:
                        result["price"] = amount
                        break
    except Exception as e:
        print(f"❌ OpenBDエラー: {e}")

    # ========== Google Books Fallback ==========
    google_url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}&key={GOOGLE_API_KEY}"
    try:
        res = requests.get(google_url)
        if res.status_code == 200:
            g_data = res.json()
            if g_data["totalItems"] > 0:
                item = g_data["items"][0]["volumeInfo"]
                result["title"] = result["title"] or item.get("title", "")
                result["author"] = result["author"] or ", ".join(item.get("authors", []))
                result["publisher"] = result["publisher"] or item.get("publisher", "")
                result["pub_date"] = result["pub_date"] or item.get("publishedDate", "").replace("-", "")
                result["summary"] = result["summary"] or item.get("description", "")
                result["cover"] = result["cover"] or item.get("imageLinks", {}).get("thumbnail", "")
                result["pages"] = result["pages"] or str(item.get("pageCount", ""))
    except Exception as e:
        print(f"❌ Google Booksエラー: {e}")

    # ========== 最低限のチェック ==========
    if not result["title"] and not result["author"]:
        raise Exception("書籍情報が見つかりませんでした")

    return result
