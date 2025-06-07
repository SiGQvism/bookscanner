import requests, pprint
isbn = "9784331523087"      # ← 調べたい ISBN
data = requests.get(f"https://api.openbd.jp/v1/get?isbn={isbn}").json()
pprint.pprint(data)
