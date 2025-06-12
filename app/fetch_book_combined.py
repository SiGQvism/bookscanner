import os, requests
from dotenv import load_dotenv

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")   # 空でも匿名アクセス可（低レート）

def _fill_if_empty(result: dict, key: str, value: str):
    """空文字だったら value を入れる"""
    if value and not result[key]:
        result[key] = value

def fetch_book_combined(isbn: str) -> dict:
    result = {
        "isbn":      isbn,
        "title":     "",
        "author":    "",
        "publisher": "",
        "pub_date":  "",
        "pages":     "",
        "price":     "",
        "summary":   "",
        "cover":     "",
    }

    # ---------- 1. OpenBD ----------
    try:
        r = requests.get(f"https://api.openbd.jp/v1/get?isbn={isbn}", timeout=5)
        if r.ok and r.json()[0]:
            ob = r.json()[0]
            s  = ob.get("summary", {})
            _fill_if_empty(result, "title",     s.get("title"))
            _fill_if_empty(result, "author",    s.get("author"))
            _fill_if_empty(result, "publisher", s.get("publisher"))
            _fill_if_empty(result, "pub_date",  s.get("pubdate"))
            _fill_if_empty(result, "cover",     s.get("cover"))

            # Extent – ページ数
            for ext in ob.get("onix", {}).get("DescriptiveDetail", {}).get("Extent", []):
                if ext.get("ExtentUnit") == "03":
                    _fill_if_empty(result, "pages", ext.get("ExtentValue"))
                    break

            # Price
            for p in ob.get("onix", {}).get("ProductSupply", {}).get("SupplyDetail", {}).get("Price", []):
                if p.get("PriceAmount"):
                    _fill_if_empty(result, "price", p["PriceAmount"])
                    break
    except Exception as e:
        print("❌ OpenBD:", e)

    # ---------- 2. Google Books ----------
    try:
        g_url = (
            "https://www.googleapis.com/books/v1/volumes"
            f"?q=isbn:{isbn}&projection=full&maxResults=1"
            f"{'&key='+GOOGLE_API_KEY if GOOGLE_API_KEY else ''}"
        )
        g = requests.get(g_url, timeout=5)
        if g.ok and g.json().get("totalItems"):
            info = g.json()["items"][0]["volumeInfo"]
            _fill_if_empty(result, "title",     info.get("title"))
            _fill_if_empty(result, "author",    ", ".join(info.get("authors", [])))
            _fill_if_empty(result, "publisher", info.get("publisher"))
            _fill_if_empty(result, "pub_date",  info.get("publishedDate", "").replace("-", ""))
            _fill_if_empty(result, "summary",   info.get("description"))
            _fill_if_empty(result, "pages",     str(info.get("pageCount", "")))

            if not result["cover"]:
                img = info.get("imageLinks", {})
                for key in ("extraLarge","large","medium","thumbnail","smallThumbnail"):
                    if img.get(key):
                        result["cover"] = img[key].replace("http://", "https://")
                        break
    except Exception as e:
        print("❌ Google Books:", e)

    # ---------- 3. 最低限チェック ----------
    if not (result["title"] or result["author"]):
        raise Exception("書籍情報が見つかりませんでした")

    return result
