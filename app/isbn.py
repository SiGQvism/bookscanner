import requests

GOOGLE = "https://www.googleapis.com/books/v1/volumes"
OPENBD = "https://api.openbd.jp/v1/get"


# ----------------------------
# OpenBD から書籍情報取得
def parse_openbd(j: dict, isbn: str) -> dict:
    onix = j.get("onix", {})
    summary = j.get("summary", {})

    title = summary.get("title") or (
        onix.get("DescriptiveDetail", {})
            .get("TitleDetail", {})
            .get("TitleElement", {})
            .get("TitleText", {})
            .get("content", "")
    )

    contributors = onix.get("DescriptiveDetail", {}).get("Contributor", [])
    author = ""
    if contributors and isinstance(contributors, list):
        person = contributors[0].get("PersonName", {})
        author = person.get("content", "") if isinstance(person, dict) else ""

    publisher = onix.get("PublishingDetail", {}) \
                    .get("Imprint", {}) \
                    .get("ImprintName", "")

    pub_date_list = onix.get("PublishingDetail", {}).get("PublishingDate", [])
    pub_date = pub_date_list[0].get("Date", "") if pub_date_list else ""

    price_list = onix.get("ProductSupply", {}).get("SupplyDetail", {}).get("Price", [])
    price = price_list[0].get("PriceAmount", "") if price_list else ""

    desc = summary.get("description", "")

    return {
        "isbn": isbn,
        "title": title,
        "author": author,
        "publisher": publisher,
        "pub_date": pub_date,
        "price": price,
        "pages": "",       # OpenBDでは取得不可
        "summary": desc,
        "cover": ""        # OpenBDでは取得不可
    }


# ----------------------------
# Google Books から補完データ取得
def parse_google(j: dict, isbn: str) -> dict:
    volume = j.get("volumeInfo", {})
    image_links = volume.get("imageLinks", {})

    return {
        "isbn": isbn,
        "title": volume.get("title", ""),
        "author": ", ".join(volume.get("authors", [])),
        "publisher": volume.get("publisher", ""),
        "pub_date": volume.get("publishedDate", "").replace("-", ""),
        "price": "",  # 価格は Google Books では取れない
        "pages": str(volume.get("pageCount", "")),
        "summary": volume.get("description", ""),
        "cover": image_links.get("thumbnail", "")
    }


# ----------------------------
# 統合フェッチ関数（OpenBD優先 → Google補完）
def fetch_book(isbn: str) -> dict:
    base = {
        "isbn": isbn, "title": "", "author": "", "publisher": "", "pub_date": "",
        "price": "", "pages": "", "summary": "", "cover": ""
    }

    # OpenBD（最優先）
    try:
        r = requests.get(f"{OPENBD}?isbn={isbn}")
        r.raise_for_status()
        j = r.json()[0]
        if j:
            base.update(parse_openbd(j, isbn))
    except Exception as e:
        print(f"openBD取得エラー: {e}")

    # Googleで補完
    try:
        g = requests.get(GOOGLE, params={"q": f"isbn:{isbn}"})
        g.raise_for_status()
        data = g.json()
        if data.get("totalItems"):
            google_data = parse_google(data["items"][0], isbn)
            for k, v in google_data.items():
                if not base.get(k):
                    base[k] = v
    except Exception as e:
        print(f"Google Books取得エラー: {e}")

    if not base["title"]:
        raise ValueError("openBD / Google Books どちらにも書籍が見つかりません")

    return base
