import json
with open("next-data.json", "r", encoding="utf-8") as f:
    data = json.load(f)
product_cards = data["props"]["pageProps"]["$dehydratedState"]["queries"][4]["state"]["data"]["productCards"]
print('count', len(product_cards))
print(product_cards[0])
