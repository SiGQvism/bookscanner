import requests

def fetch_book(isbn):
    # Google Books優先
    google_url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
    res = requests.get(google_url)
    if res.status_code == 200 and res.json()["totalItems"] > 0:
        item = res.json()["items"][0]["volumeInfo"]
        return {
            "title": item.get("title", ""),
            "author": ", ".join(item.get("authors", [])),
            "publisher": item.get("publisher", ""),
            "pub_date": item.get("publishedDate", "").replace("-", ""),
            "price": "0",
            "pages": str(item.get("pageCount", "")),
            "summary": item.get("description", ""),  # ✅ descriptionを優先
            "cover": item.get("imageLinks", {}).get("thumbnail", ""),
            "isbn": isbn
        }

    # Fallback: OpenBD
    openbd_url = f"https://api.openbd.jp/v1/get?isbn={isbn}"
    res = requests.get(openbd_url)
    if res.status_code == 200 and res.json()[0] is not None:
        item = res.json()[0]
        summary = item["summary"]
        price = ""
        try:
            price = item["onix"]["ProductSupply"]["SupplyDetail"]["Price"][0]["PriceAmount"]
        except:
            price = ""

        return {
            "title": summary.get("title", ""),
            "author": summary.get("author", ""),
            "publisher": summary.get("publisher", ""),
            "pub_date": summary.get("pubdate", ""),
            "price": price,
            "pages": summary.get("pages", ""),
            "summary": summary.get("volume", ""),
            "cover": summary.get("cover", ""),
            "isbn": isbn
        }

    raise Exception("書籍情報が見つかりませんでした")
