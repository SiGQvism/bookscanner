import requests

def fetch_book_combined(isbn: str) -> dict:
    data = {
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

    # OpenBDから取得
    openbd_url = f"https://api.openbd.jp/v1/get?isbn={isbn}"
    res = requests.get(openbd_url)
    if res.status_code == 200 and res.json()[0] is not None:
        ob = res.json()[0]

        summary = ob.get("summary", {})
        data.update({
            "title": summary.get("title", ""),
            "author": summary.get("author", ""),
            "publisher": summary.get("publisher", ""),
            "pub_date": summary.get("pubdate", ""),
            "cover": summary.get("cover", "")
        })

        # Extent処理を強化
        extent_info = data.get("onix", {}).get("DescriptiveDetail", {}).get("Extent", [])

        # Extentがdictの場合も対応
        if isinstance(extent_info, dict):
            extent_info = [extent_info]

        for item in extent_info:
            if item.get("ExtentUnit") == "03":
                result["pages"] = item.get("ExtentValue", "")
                break  # 最初に見つけたページ数を採用

        # 価格
        prices = ob.get("onix", {}).get("ProductSupply", {}).get("SupplyDetail", {}).get("Price", [])
        if isinstance(prices, list) and prices:
            data["price"] = prices[0].get("PriceAmount", "")

    # Google Books 補完
    google_url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
    res = requests.get(google_url)
    if res.status_code == 200 and res.json().get("totalItems", 0) > 0:
        item = res.json()["items"][0]["volumeInfo"]
        data.update({
            "title": data["title"] or item.get("title", ""),
            "author": data["author"] or ", ".join(item.get("authors", [])),
            "publisher": data["publisher"] or item.get("publisher", ""),
            "pub_date": data["pub_date"] or item.get("publishedDate", "").replace("-", ""),
            "summary": data["summary"] or item.get("description", ""),
            "cover": data["cover"] or item.get("imageLinks", {}).get("thumbnail", ""),
            "pages": data["pages"] or str(item.get("pageCount", ""))
        })

    if not data["title"] and not data["author"]:
        raise Exception("書籍情報が見つかりませんでした")

    return data
