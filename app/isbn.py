import requests

def fetch_book(isbn: str) -> dict:
    # --- OpenBD APIで取得 ---
    res = requests.get(f"https://api.openbd.jp/v1/get?isbn={isbn}")
    data = res.json()[0]

    # --- OpenBDにデータがない場合はGoogle Booksにフォールバック ---
    if data is None:
        g_res = requests.get(f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}")
        g_data = g_res.json()

        if "items" not in g_data:
            raise ValueError("書籍情報が見つかりませんでした")

        volume = g_data["items"][0]["volumeInfo"]

        return {
            "isbn": isbn,
            "title": volume.get("title", ""),
            "author": ", ".join(volume.get("authors", [])),
            "publisher": volume.get("publisher", ""),
            "pub_date": volume.get("publishedDate", "").replace("-", ""),
            "price": "0",  # Google Booksには価格情報がないため仮置き
            "pages": str(volume.get("pageCount", "")),
            "summary": volume.get("description", ""),
            "cover": volume.get("imageLinks", {}).get("thumbnail", "")
        }

    # --- OpenBDのデータ構造から情報を取り出す ---
    summary = data.get("summary", {})
    onix = data.get("onix", {})
    coll = data.get("collation", "")

    return {
        "isbn": isbn,
        "title": summary.get("title", ""),
        "author": summary.get("author", ""),
        "publisher": summary.get("publisher", ""),
        "pub_date": summary.get("pubdate", ""),
        "price": str(summary.get("price", "0")),
        "pages": coll if isinstance(coll, str) else "",
        "summary": onix.get("CollateralDetail", {}).get("TextContent", [{}])[0].get("Text", ""),
        "cover": summary.get("cover", "")
    }
