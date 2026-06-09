"""
agent.py — FitFindr planning loop
"""

import re
from tools import search_listings, suggest_outfit, create_fit_card


def _new_session(query: str, wardrobe: dict) -> dict:
    return {
        "query": query,
        "parsed": {},
        "search_results": [],
        "selected_item": None,
        "wardrobe": wardrobe,
        "outfit_suggestion": None,
        "fit_card": None,
        "error": None,
    }


def _parse_query(query: str) -> dict:
    """Extract description, size, and max_price from a natural language query."""
    q = query.lower()

    # Extract max_price (e.g. "under $30", "under 30")
    price_match = re.search(r"under\s+\$?(\d+(?:\.\d+)?)", q)
    max_price = float(price_match.group(1)) if price_match else None

    # Extract size (e.g. "size M", "size 8", "size W30")
    size_match = re.search(r"size\s+([a-zA-Z0-9\/]+)", query, re.IGNORECASE)
    size = size_match.group(1) if size_match else None

    # Description: remove price and size fragments to get clean keywords
    description = re.sub(r"under\s+\$?\d+(?:\.\d+)?", "", q)
    description = re.sub(r"size\s+[a-zA-Z0-9\/]+", "", description, flags=re.IGNORECASE)
    description = re.sub(r"[^\w\s]", " ", description).strip()

    return {"description": description, "size": size, "max_price": max_price}


def run_agent(query: str, wardrobe: dict) -> dict:
    # Step 1: Initialize session
    session = _new_session(query, wardrobe)

    # Step 2: Parse query
    parsed = _parse_query(query)
    session["parsed"] = parsed

    # Step 3: Search listings
    results = search_listings(
        parsed["description"],
        size=parsed["size"],
        max_price=parsed["max_price"],
    )
    session["search_results"] = results

    if not results:
        session["error"] = (
            "No listings found for your search. Try broadening your description, "
            "adjusting your size, or raising your price limit."
        )
        return session

    # Step 4: Select top result
    session["selected_item"] = results[0]

    # Step 5: Suggest outfit
    session["outfit_suggestion"] = suggest_outfit(results[0], wardrobe)

    # Step 6: Create fit card
    session["fit_card"] = create_fit_card(session["outfit_suggestion"], results[0])

    return session


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")
