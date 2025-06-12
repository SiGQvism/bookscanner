"""
fetch_book_combined.py
---------------------------------
OpenBD → Google Books の 2 段構えで
(1) 出来るだけ網羅的にメタデータを集め  
(2) OpenBD の値を優先しつつ欠けている所だけ Google で補完
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")   # 無料枠でも OK。ただしレートは低い


def _try_google(isbn: str, result: dict) -> None:
    """
    Google Books から出来るだけ “完全版” を取得し、
    result でまだ空いている項目だけを埋める
    """
    url = (
        "https://www.googleapis.com/books/v1/volumes"
        f"?q=isbn:{isbn}&projection=full&maxResults=1"
        f"{'&key=' + GOOGLE_API_KEY if GOOGLE_API_KEY else ''}"
    )

    try:
        r = requests.get(url, timeout=5)
        if r.status_code != 200:
            return
        data = r.json()
        if data.get("totalItems", 0) == 0:
            return

        info = data["items"][0]["volumeInfo"]

        # setdefault() で “未設定なら入れる” ＝ OpenBD 優先を維持
        result.setdefault("title",      info.get("title", ""))
        result.setdefault("author",     ", ".join(info.get("authors", [])))
        result.setdefault("publisher",  info.get("publisher", ""))
        result.setdefault("pub_date",   info.get("publishedDate", "").replace("-", ""))
        result.setdefault("summary",    info.get("description", ""))
        if not result.get("pages") and info.get("pageCount"):
            result["pages"] = str(info["pageCount"])

        if not result.get("cover"):
            links = info.get("imageLinks", {})
            for key in ("extraLarge", "large", "medium", "thumbnail", "smallThumbnail"):
                url = links.get(key)
                if url:
                    result["cover"] = url.replace("http://", "https://")
                    break

    except Exception as e:
        print("❌ Google Books エラー:", e)


def fetch_book_combined(isbn: str) -> dict:
    """
    可能な限り埋まった書誌情報 dict を返す。
    優先順位: ①OpenBD → ②Google Books
    """
    result = {
        "isbn":       isbn,
        "title":      "",
        "author":     "",
        "publisher":  "",
        "pub_date":   "",
        "pages":      "",
        "price":      "",
        "summary":    "",
        "cover":      ""
    }

    # ---------- OpenBD ----------
    openbd_url = f"https://api.openbd.jp/v1/get?isbn={isbn}"
    try:
        r = requests.get(openbd_url, timeout=5)
        if r.status_code == 200:
            ob = r.json()[0]
            if ob:
                summ = ob.get("summary", {})
                result["title"]      = summ.get("title",     "") or result["title"]
                result["author"]     = summ.get("author",    "") or result["author"]
                result["publisher"]  = summ.get("publisher", "") or result["publisher"]
                result["pub_date"]   = summ.get("pubdate",   "") or result["pub_date"]
                result["cover"]      = summ.get("cover",     "") or result["cover"]

                # ページ数（ExtentUnit==03）
                ext = ob.get("onix", {}).get("DescriptiveDetail", {}).get("Extent", [])
                if isinstance(ext, dict):
                    ext = [ext]
                for e in ext:
                    if e.get("ExtentUnit") == "03":
                        result["pages"] = e.get("ExtentValue", "")
                        break

                # 価格（最初に見つけた PriceAmount）
                prices = ob.get("onix", {}).get("ProductSupply", {}).get("SupplyDetail", {}).get("Price", [])
                if isinstance(prices, dict):
                    prices = [prices]
                for p in prices:
                    amt = p.get("PriceAmount")
                    if amt:
                        result["price"] = amt
                        break
    except Exception as e:
        print("❌ OpenBD エラー:", e)

    # ---------- Google Books フォールバック ----------
    _try_google(isbn, result)

    # ---------- 最小限チェック ----------
    if not (result["title"] or result["author"]):
        raise Exception("書籍情報が見つかりませんでした")

    return result
