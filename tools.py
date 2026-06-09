"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    listings = load_listings()

    filtered = []
    for item in listings:
        if max_price is not None and item["price"] > max_price:
            continue
        if size is not None and size.lower() not in item["size"].lower():
            continue
        filtered.append(item)

    keywords = description.lower().split()
    scored = []
    for item in filtered:
        searchable = " ".join([
            item.get("title", ""),
            item.get("description", ""),
            " ".join(item.get("style_tags", [])),
        ]).lower()
        score = sum(1 for kw in keywords if kw in searchable)
        if score > 0:
            scored.append((score, item))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    client = _get_groq_client()

    item_summary = (
        f"{new_item.get('title')} — {new_item.get('category')}, "
        f"colors: {', '.join(new_item.get('colors', []))}, "
        f"style tags: {', '.join(new_item.get('style_tags', []))}"
    )

    if not wardrobe.get("items"):
        prompt = (
            f"A user is considering buying this secondhand item: {item_summary}. "
            f"They haven't shared their wardrobe yet. Give them 2-3 sentences of "
            f"general styling advice — what types of pieces it pairs well with, "
            f"what aesthetic it suits, and how to wear it."
        )
    else:
        wardrobe_lines = "\n".join(
            f"- {w.get('name')} ({w.get('category')}, colors: {', '.join(w.get('colors', []))})"
            for w in wardrobe["items"]
        )
        prompt = (
            f"A user is considering buying this secondhand item: {item_summary}.\n\n"
            f"Their current wardrobe includes:\n{wardrobe_lines}\n\n"
            f"Suggest 1-2 complete outfit combinations using the new item and "
            f"specific named pieces from their wardrobe. Be specific and casual."
        )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
    )
    return response.choices[0].message.content or "Could not generate outfit suggestion. Please try again."


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    if not outfit or not outfit.strip():
        return "Cannot generate a fit card without an outfit suggestion. Please retry your search."

    client = _get_groq_client()

    title = new_item.get("title", "this piece")
    price = new_item.get("price", "")
    platform = new_item.get("platform", "a thrift platform")

    prompt = (
        f"Write a 2-4 sentence Instagram/TikTok caption for this outfit:\n\n"
        f"Thrifted item: {title}, found on {platform} for ${price}\n"
        f"Outfit: {outfit}\n\n"
        f"Rules: casual first-person voice, mention the item name, price, and platform "
        f"naturally (once each), capture the specific vibe. Sound like a real OOTD post, "
        f"not a product description. No hashtags."
    )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150,
        temperature=0.9,
    )
    return response.choices[0].message.content or "Could not generate fit card. Please try again."
