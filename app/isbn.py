import requests

def fetch_book(isbn):
    result = {
        "title": "",
        "author": "",
        "publisher": "",
        "pub_date": "",
        "price": "",
        "pages": "",
        "summary": "",
        "cover": "",
        "isbn": isbn
    }

    # ① OpenBD
    openbd_url = f"https://api.openbd.jp/v1/get?isbn={isbn}"
    res = requests.get(openbd_url)
    if res.status_code == 200 and res.json()[0] is not None:
        summary = res.json()[0]["summary"]
        result.update({
            "title": summary.get("title", ""),
            "author": summary.get("author", ""),
            "publisher": summary.get("publisher", ""),
            "pub_date": summary.get("pubdate", ""),
            "price": summary.get("price", ""),
            "pages": summary.get("pages", ""),
            "cover": summary.get("cover", "")
        })

    # ② Google Books（補完用）
    google_url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
    res = requests.get(google_url)
    if res.status_code == 200 and res.json()["totalItems"] > 0:
        item = res.json()["items"][0]["volumeInfo"]
        result.update({
            "title": result["title"] or item.get("title", ""),
            "author": result["author"] or ", ".join(item.get("authors", [])),
            "publisher": result["publisher"] or item.get("publisher", ""),
            "pub_date": result["pub_date"] or item.get("publishedDate", "").replace("-", ""),
            "summary": result["summary"] or item.get("description", ""),
            "cover": result["cover"] or item.get("imageLinks", {}).get("thumbnail", "")
        })

    if not result["title"] and not result["author"]:
        raise Exception("書籍情報が見つかりませんでした")

    return result
