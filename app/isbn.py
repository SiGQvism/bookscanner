import requests

def fetch_book(isbn: str) -> dict:
    isbn = isbn.replace("-", "")
    data = {}

    # --- OpenBDから取得 ---
    openbd_url = f"https://api.openbd.jp/v1/get?isbn={isbn}"
    res = requests.get(openbd_url)
    if res.status_code == 200:
        items = res.json()
        if items and items[0] is not None:
            summary = items[0]["summary"]
            data["title"] = summary.get("title", "")
            data["author"] = summary.get("author", "")
            data["publisher"] = summary.get("publisher", "")
            data["pub_date"] = summary.get("pubdate", "")
            data["cover"] = summary.get("cover", "")
            data["isbn"] = isbn
            data["price"] = ""
            data["pages"] = ""
            data["summary"] = ""
            return data  # ✅ 成功時ここで終了

    # --- Google Books API で補完 ---
    gb_url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
    res = requests.get(gb_url)
    if res.status_code == 200:
        items = res.json().get("items")
        if items:
            volume = items[0]["volumeInfo"]
            data["title"] = volume.get("title", "")
            data["author"] = ", ".join(volume.get("authors", []))
            data["publisher"] = volume.get("publisher", "")
            data["pub_date"] = volume.get("publishedDate", "").replace("-", "")
            data["cover"] = volume.get("imageLinks", {}).get("thumbnail", "")
            data["summary"] = volume.get("description", "")
            data["pages"] = str(volume.get("pageCount", ""))
            data["price"] = ""
            data["isbn"] = isbn
            return data

    # --- 失敗時 ---
    raise ValueError("書籍情報を取得できませんでした。")
