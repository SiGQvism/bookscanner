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

    openbd_url = f"https://api.openbd.jp/v1/get?isbn={isbn}"
    res = requests.get(openbd_url)
    if res.status_code == 200 and res.json()[0] is not None:
        data = res.json()[0]

        # summaryから取得
        summary = data.get("summary", {})
        result.update({
            "title": summary.get("title", ""),
            "author": summary.get("author", ""),
            "publisher": summary.get("publisher", ""),
            "pub_date": summary.get("pubdate", ""),
            "cover": summary.get("cover", "")
        })

        # onixからページ数と価格取得
        extent_info = data.get("onix", {}).get("DescriptiveDetail", {}).get("Extent", [])
        for item in extent_info:
            if item.get("ExtentUnit") == "03":
                result["pages"] = item.get("ExtentValue")

        prices = data.get("onix", {}).get("ProductSupply", {}).get("SupplyDetail", {}).get("Price", [])
        if isinstance(prices, list) and prices:
            result["price"] = prices[0].get("PriceAmount", "")

    # Google Books 補完
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
            "cover": result["cover"] or item.get("imageLinks", {}).get("thumbnail", ""),
            "pages": result["pages"] or str(item.get("pageCount", "")),
        })

    if not result["title"] and not result["author"]:
        raise Exception("書籍情報が見つかりませんでした")

    return result
