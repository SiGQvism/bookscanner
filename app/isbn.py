import requests

def fetch_book(isbn):
    # OpenBD API
    openbd_url = f"https://api.openbd.jp/v1/get?isbn={isbn}"
    res = requests.get(openbd_url)
    if res.status_code == 200 and res.json()[0] is not None:
        data = res.json()[0]["summary"]
        return {
            "title": data.get("title", ""),
            "author": data.get("author", ""),
            "publisher": data.get("publisher", ""),
            "pub_date": data.get("pubdate", ""),
            "price": data.get("price", ""),
            "pages": data.get("pages", ""),
            "summary": data.get("volume", ""),
            "cover": data.get("cover", ""),
            "isbn": isbn
        }

    # Google Books API fallback
    google_url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
    res = requests.get(google_url)
    if res.status_code == 200 and res.json()["totalItems"] > 0:
        item = res.json()["items"][0]["volumeInfo"]
        return {
            "title": item.get("title", ""),
            "author": ", ".join(item.get("authors", [])),
            "publisher": item.get("publisher", ""),
            "pub_date": item.get("publishedDate", "").replace("-", ""),
            "price": "0",  # Google Booksには価格情報がない
            "pages": str(item.get("pageCount", "")),
            "summary": item.get("description", ""),
            "cover": item.get("imageLinks", {}).get("thumbnail", ""),
            "isbn": isbn
        }

    raise Exception("書籍情報が見つかりませんでした")
