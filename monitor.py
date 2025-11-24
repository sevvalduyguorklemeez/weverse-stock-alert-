"""
Automated watcher for the Weverse PPULBATU category.

Fetches the category page, parses the embedded Next.js data to obtain all
product cards, compares them with the previous snapshot, and sends email
alerts for restocks or price drops.
"""

import json
import re
import smtplib
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, List, Tuple

import requests

BASE_URL = "https://shop.weverse.io/en/shop/USD/artists/3"
STATE_FILE = Path("state.json")
CONFIG_FILE = Path("config.json")

# Map category ids to human readable labels (from TXT artist shop)
CATEGORY_MAP = {
    6426: "2025 BLACK FRIDAY",
    6256: "PPULBATU",
    6: "MERCH",
    5: "ALBUM",
    186: "TOUR MERCH",
    44: "DVD/MEDIA",
    65: "GLOBAL MEMBERSHIP",
    112: "JAPAN MEMBERSHIP",
    80: "US MEMBERSHIP",
    776: "SEASON'S GREETINGS",
    392: "WEVERSE",
    6216: "WEVERSE MERCH",
}
CATEGORY_IDS = list(CATEGORY_MAP.keys())


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(
            f"Config file {CONFIG_FILE} is missing. "
            "Copy config.example.json to config.json and fill in your SMTP info."
        )
    with CONFIG_FILE.open(encoding="utf-8") as fh:
        return json.load(fh)


def fetch_product_cards(category_id: int) -> List[dict]:
    url = f"{BASE_URL}?categoryId={category_id}"
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    match = re.search(
        r'id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        response.text,
        re.DOTALL,
    )
    if not match:
        raise RuntimeError("Could not locate __NEXT_DATA__ payload in the page.")

    data = json.loads(match.group(1))
    queries = data["props"]["pageProps"]["$dehydratedState"]["queries"]
    for query in queries:
        state_data = query.get("state", {}).get("data", {})
        if (
            isinstance(state_data, dict)
            and state_data.get("productCards")
            and query.get("state", {}).get("data", {}).get("lastIdx") is not None
        ):
            return state_data["productCards"]

    raise RuntimeError(f"productCards not found in category {category_id}.")


def fetch_all_product_cards() -> List[dict]:
    all_cards: List[dict] = []
    for category_id in CATEGORY_IDS:
        try:
            cards = fetch_product_cards(category_id)
        except Exception as exc:  # pragma: no cover - best effort per category
            print(f"[monitor] Failed to fetch category {category_id}: {exc}")
            continue
        for card in cards:
            card["_categoryId"] = category_id
            card["_categoryName"] = CATEGORY_MAP.get(category_id, str(category_id))
            all_cards.append(card)
    return all_cards


def simplify(cards: List[dict]) -> Dict[str, dict]:
    simplified = {}
    for card in cards:
        sale_id = str(card.get("saleId"))
        category_id = card.get("_categoryId")
        key = f"{category_id}:{sale_id}"
        simplified[key] = {
            "name": card.get("name"),
            "status": card.get("status"),
            "price": card.get("price", {}).get("salePrice"),
            "originalPrice": card.get("price", {}).get("originalPrice"),
            "categoryId": category_id,
            "categoryName": card.get("_categoryName"),
            "url": f"https://shop.weverse.io/en/shop/USD/artists/3/sales/{sale_id}",
        }
    return simplified


def load_previous_state() -> Dict[str, dict]:
    if not STATE_FILE.exists():
        return {}
    with STATE_FILE.open(encoding="utf-8") as fh:
        return json.load(fh)


def save_state(state: Dict[str, dict]) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def detect_changes(
    previous: Dict[str, dict], current: Dict[str, dict]
) -> List[Tuple[str, dict, dict]]:
    changes = []
    for key, current_entry in current.items():
        prev_entry = previous.get(key)
        if not prev_entry:
            continue  # treat first observation as baseline
        restocked = (
            prev_entry.get("status") == "SOLD_OUT"
            and current_entry.get("status") != "SOLD_OUT"
        )
        price_drop = (
            prev_entry.get("price") is not None
            and current_entry.get("price") is not None
            and current_entry["price"] < prev_entry["price"]
        )
        if restocked or price_drop:
            changes.append((sale_id, prev_entry, current_entry))
    return changes


def format_digest(changes: List[Tuple[str, dict, dict]]) -> str:
    lines = []
    for _, prev, curr in changes:
        name = curr.get("name")
        url = curr.get("url")
        status_line = f"{prev.get('status')} -> {curr.get('status')}"
        price_line = f"{prev.get('price')} -> {curr.get('price')}"
        category = curr.get("categoryName") or curr.get("categoryId")
        lines.append(
            f"{name} ({category})\n"
            f"Status: {status_line}\n"
            f"Price: {price_line}\n"
            f"Link: {url}\n"
        )
    return "\n".join(lines)


def send_email(subject: str, body: str, config: dict) -> None:
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = config["sender"]
    msg["To"] = ", ".join(config["recipients"])

    with smtplib.SMTP(config["smtp_host"], config["smtp_port"], timeout=30) as smtp:
        if config.get("use_tls", True):
            smtp.starttls()
        if config.get("smtp_user") and config.get("smtp_password"):
            smtp.login(config["smtp_user"], config["smtp_password"])
        smtp.sendmail(config["sender"], config["recipients"], msg.as_string())


def main() -> None:
    config = load_config()
    cards = fetch_all_product_cards()
    current_state = simplify(cards)
    previous_state = load_previous_state()

    if not previous_state:
        save_state(current_state)
        print("Saved initial snapshot. No alerts sent on the first run.")
        return

    changes = detect_changes(previous_state, current_state)
    if not changes:
        print("No changes detected.")
        save_state(current_state)
        return

    body = format_digest(changes)
    send_email(
        subject="Weverse stock alert",
        body=body,
        config=config,
    )
    print(f"Sent {len(changes)} alert(s).")
    save_state(current_state)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover
        print(f"[monitor] Failed: {exc}")

