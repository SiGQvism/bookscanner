import os, requests, json
from dotenv import load_dotenv

load_dotenv()
GB_KEY = os.getenv("GOOGLE_API_KEY", "")      # 無ければ匿名

FIELDS = (
    "isbn title author publisher pub_date pages "
    "price summary cover"
).split()

def put(res: dict, key: str, val):
    """None/空/0 以外なら文字列化して上書き"""
    if val in (None, "", 0):          # “0 円” も許容したいならここを変更
        return
    res[key] = str(val)

def fetch_book_combined(isbn: str) -> dict:
    res = {k: "" for k in FIELDS}
    res["isbn"] = isbn

    # ---------- OpenBD ----------
    try:
        ob = requests.get(f"https://api.openbd.jp/v1/get?isbn={isbn}", timeout=4).json()[0]
        if ob:
            s = ob.get("summary", {})
            put(res, "title",     s.get("title"))
            put(res, "author",    s.get("author"))
            put(res, "publisher", s.get("publisher"))
            put(res, "pub_date",  s.get("pubdate"))
            put(res, "cover",     s.get("cover"))

            for ext in ob.get("onix", {}).get("DescriptiveDetail", {}).get("Extent", []):
                if ext.get("ExtentUnit") == "03":
                    put(res, "pages", ext.get("ExtentValue")); break

            for p in ob.get("onix", {}).get("ProductSupply", {}).get("SupplyDetail", {}).get("Price", []):
                put(res, "price", p.get("PriceAmount")); break
    except Exception as e:
        print("OpenBD ✖", e)

    # ---------- Google Books ----------
    try:
        g = requests.get(
            "https://www.googleapis.com/books/v1/volumes",
            params={
                "q": f"isbn:{isbn}",
                "projection": "full",
                "maxResults": 1,
                **({"key": GB_KEY} if GB_KEY else {})
            },
            timeout=4
        ).json()
        if g.get("totalItems"):
            v = g["items"][0]["volumeInfo"]
            put(res, "title",     v.get("title"))
            put(res, "author",    ", ".join(v.get("authors", [])))
            put(res, "publisher", v.get("publisher"))
            put(res, "pub_date",  v.get("publishedDate", "").replace("-", ""))
            put(res, "summary",   v.get("description"))
            put(res, "pages",     v.get("pageCount"))

            if not res["cover"]:
                img = v.get("imageLinks", {})
                # 解像度が高い順に取り、必ず https 化
                for k in ("extraLarge", "large", "medium",
                          "thumbnail", "smallThumbnail"):
                    if k in img:
                        put(res, "cover", img[k].replace("http://", "https://"))
                        break
    except Exception as e:
        print("Google ✖", e)

    # ---------- フォールバック最終確認 ----------
    if not (res["title"] or res["author"]):
        raise RuntimeError("書籍情報が見つかりませんでした")

    return res
