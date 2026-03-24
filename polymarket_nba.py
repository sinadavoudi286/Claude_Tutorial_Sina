import requests

def fetch_nba_markets():
    """Fetch NBA-related prediction markets from Polymarket."""
    url = "https://gamma-api.polymarket.com/markets"
    params = {
        "limit": 100,
        "active": "true",
        "closed": "false",
        "tag_slug": "nba",
    }

    all_markets = []
    offset = 0

    print("Fetching NBA markets from Polymarket...\n")

    while True:
        params["offset"] = offset
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            markets = response.json()
        except requests.RequestException as e:
            print(f"Request failed: {e}")
            break

        if not markets:
            break

        all_markets.extend(markets)

        if len(markets) < params["limit"]:
            break
        offset += params["limit"]

    # Fallback: also search by keyword in case tag didn't catch everything
    if not all_markets:
        print("No results via tag, trying keyword search...\n")
        params_kw = {
            "limit": 100,
            "active": "true",
            "closed": "false",
            "q": "NBA",
        }
        try:
            response = requests.get(url, params=params_kw, timeout=10)
            response.raise_for_status()
            all_markets = response.json()
        except requests.RequestException as e:
            print(f"Keyword search failed: {e}")

    if not all_markets:
        print("No NBA markets found.")
        return

    print(f"Found {len(all_markets)} NBA market(s):\n")
    print(f"{'#':<4} {'Question':<80} {'Volume':>12}  {'Ends'}")
    print("-" * 120)

    for i, market in enumerate(all_markets, 1):
        question = market.get("question", "N/A")
        volume = market.get("volume", 0)
        end_date = market.get("endDate", "N/A")
        if end_date and end_date != "N/A":
            end_date = end_date[:10]  # trim to YYYY-MM-DD

        # Truncate long questions
        if len(question) > 78:
            question = question[:75] + "..."

        try:
            volume_str = f"${float(volume):,.0f}"
        except (ValueError, TypeError):
            volume_str = "N/A"

        print(f"{i:<4} {question:<80} {volume_str:>12}  {end_date}")

    print()


if __name__ == "__main__":
    fetch_nba_markets()
