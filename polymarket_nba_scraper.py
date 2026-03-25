#!/usr/bin/env python3
"""
Polymarket NBA Markets Scraper
Fetches NBA-related prediction markets and saves them to a CSV file.
"""

import requests
import json
import csv
from datetime import datetime


GAMMA_API_BASE = "https://gamma-api.polymarket.com"


def fetch_all_markets(batch_size=200):
    """Download all active markets from Polymarket, page by page."""
    all_markets = []
    offset = 0

    print("Downloading markets from Polymarket...")

    while True:
        params = {
            "limit": batch_size,
            "offset": offset,
            "active": "true",
            "closed": "false",
        }
        response = requests.get(
            f"{GAMMA_API_BASE}/markets",
            params=params,
            timeout=15,
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        batch = response.json()

        if not batch:
            break

        all_markets.extend(batch)
        print(f"  Downloaded {len(all_markets)} markets so far...")

        if len(batch) < batch_size:
            break

        offset += batch_size

    return all_markets


def is_nba_market(market):
    """Return True only if the market question clearly mentions NBA."""
    question = market.get("question", "").lower()
    description = market.get("description", "").lower()
    group_title = market.get("groupItemTitle", "").lower()

    nba_keywords = ["nba", "lakers", "celtics", "warriors", "knicks", "nuggets",
                    "bucks", "heat", "suns", "nets", "76ers", "clippers",
                    "nba finals", "nba champion", "nba playoffs"]

    text = question + " " + description + " " + group_title
    return any(keyword in text for keyword in nba_keywords)


def save_to_csv(markets, filename):
    """Save markets to a CSV file so you can open it in Excel."""
    if not markets:
        return

    fieldnames = ["#", "Question", "Status", "End Date", "Volume ($)",
                  "Liquidity ($)", "Options", "URL"]

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for i, market in enumerate(markets, 1):
            question = market.get("question", "N/A")
            active = market.get("active", False)
            closed = market.get("closed", False)
            status = "Active" if active and not closed else "Closed"

            end_date = market.get("endDate", "")
            if end_date:
                try:
                    dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                    end_date = dt.strftime("%Y-%m-%d")
                except Exception:
                    pass

            try:
                volume = f"{float(market.get('volume', 0) or 0):,.0f}"
            except (ValueError, TypeError):
                volume = "0"

            try:
                liquidity = f"{float(market.get('liquidity', 0) or 0):,.0f}"
            except (ValueError, TypeError):
                liquidity = "0"

            outcomes = market.get("outcomes", "[]")
            if isinstance(outcomes, str):
                try:
                    outcomes = json.loads(outcomes)
                except Exception:
                    outcomes = []
            options = ", ".join(str(o) for o in outcomes)

            url = market.get("url", "")
            if url and not url.startswith("http"):
                url = f"https://polymarket.com{url}"

            writer.writerow({
                "#": i,
                "Question": question,
                "Status": status,
                "End Date": end_date,
                "Volume ($)": volume,
                "Liquidity ($)": liquidity,
                "Options": options,
                "URL": url,
            })

    print(f"\nSaved to file: {filename}")
    print(f"Open this file in Excel or Google Sheets to explore the data.")


def main():
    try:
        all_markets = fetch_all_markets()
    except requests.exceptions.ConnectionError:
        print("Error: No internet connection.")
        return
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}")
        return

    # Filter: keep only markets that actually mention NBA
    nba_markets = [m for m in all_markets if is_nba_market(m)]

    if not nba_markets:
        print("\nNo NBA markets found.")
        return

    # Sort by volume (highest trading activity first)
    nba_markets.sort(key=lambda m: float(m.get("volume", 0) or 0), reverse=True)

    print(f"\nFound {len(nba_markets)} actual NBA markets (out of {len(all_markets)} total).\n")

    # Print to terminal
    for i, market in enumerate(nba_markets, 1):
        question = market.get("question", "N/A")
        try:
            volume = f"${float(market.get('volume', 0) or 0):,.0f}"
        except (ValueError, TypeError):
            volume = "$0"
        end_date = market.get("endDate", "")[:10]
        print(f"#{i:>3}  {question}")
        print(f"       Volume: {volume}  |  Ends: {end_date}")
        print()

    # Save to CSV file in the same folder as this script
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = f"nba_markets_{timestamp}.csv"
    save_to_csv(nba_markets, filename)

    print(f"\nTotal: {len(nba_markets)} NBA markets")


if __name__ == "__main__":
    main()
