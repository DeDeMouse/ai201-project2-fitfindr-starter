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
import re

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

# Default chat model used by the LLM-backed tools.
_MODEL = "llama-3.3-70b-versatile"


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
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    listings = load_listings()

    # Tokenize the query into meaningful keywords (drop tiny stopwords).
    stopwords = {"a", "an", "the", "for", "and", "in", "of", "to", "with", "size"}
    keywords = {
        word
        for word in re.findall(r"[a-z0-9]+", description.lower())
        if word not in stopwords
    }

    requested_size = size.strip().lower() if size is not None else None

    scored: list[tuple[int, int, dict]] = []
    for index, listing in enumerate(listings):
        # --- Filter: price ceiling ---
        if max_price is not None and listing["price"] > max_price:
            continue

        # --- Filter: size — case-insensitive, whole-token match so that
        # "M" matches "S/M" or "M (oversized)" but NOT the "s" inside "US 7".
        if requested_size is not None:
            size_tokens = {
                token for token in re.split(r"[\s/()]+", listing["size"].lower()) if token
            }
            if requested_size not in size_tokens:
                continue

        # --- Score: keyword overlap against the listing's searchable text ---
        searchable = " ".join(
            [
                listing.get("title", ""),
                listing.get("description", ""),
                listing.get("category", ""),
                listing.get("brand") or "",
                " ".join(listing.get("style_tags", [])),
                " ".join(listing.get("colors", [])),
            ]
        )
        listing_words = set(re.findall(r"[a-z0-9]+", searchable.lower()))
        score = len(keywords & listing_words)
        if score == 0:
            continue

        # index keeps the sort stable for equal scores (preserves data order)
        scored.append((score, index, listing))

    scored.sort(key=lambda triple: (-triple[0], triple[1]))
    return [listing for _, _, listing in scored]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    client = _get_groq_client()

    # Describe the thrifted item the user is considering.
    item_desc = (
        f"{new_item.get('title', 'an item')} "
        f"(category: {new_item.get('category', 'clothing')}; "
        f"colors: {', '.join(new_item.get('colors', [])) or 'unspecified'}; "
        f"style: {', '.join(new_item.get('style_tags', [])) or 'unspecified'})"
    )

    items = wardrobe.get("items", [])
    if not items:
        # Empty wardrobe: ask for general styling advice instead of failing.
        prompt = (
            f"A shopper is considering buying this secondhand item:\n{item_desc}\n\n"
            "They have not saved a wardrobe yet, so you can't reference specific "
            "pieces they own. Give general styling advice: what kinds of items pair "
            "well with it, what vibe or occasions it suits, and how to dress it up or "
            "down. Keep it to a short, friendly paragraph."
        )
    else:
        # Populated wardrobe: ask for outfits using named pieces they already own.
        wardrobe_lines = "\n".join(
            f"- {it.get('name', 'item')} "
            f"(category: {it.get('category', '')}; "
            f"colors: {', '.join(it.get('colors', [])) or 'unspecified'})"
            for it in items
        )
        prompt = (
            f"A shopper is considering buying this secondhand item:\n{item_desc}\n\n"
            f"Here is their existing wardrobe:\n{wardrobe_lines}\n\n"
            "Suggest 1-2 complete outfits that combine the new item with specific, "
            "named pieces from their wardrobe. Refer to each wardrobe piece by name. "
            "Keep it concise, practical, and encouraging."
        )

    response = client.chat.completions.create(
        model=_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a friendly, knowledgeable personal stylist "
                "who specializes in secondhand and vintage fashion.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    # Guard: no usable outfit → return a descriptive message, never raise.
    if not outfit or not outfit.strip():
        return (
            "Can't create a fit card — no outfit suggestion was provided. "
            "Generate an outfit first, then try again."
        )

    client = _get_groq_client()

    title = new_item.get("title", "this piece")
    price = new_item.get("price")
    price_str = f"${price:g}" if isinstance(price, (int, float)) else "a great price"
    platform = new_item.get("platform", "secondhand")

    prompt = (
        f"Write a short, shareable Instagram/TikTok caption for a thrifted fashion find.\n\n"
        f"Item: {title}\n"
        f"Price: {price_str}\n"
        f"Platform: {platform}\n"
        f"Outfit it's styled in:\n{outfit.strip()}\n\n"
        "Guidelines:\n"
        "- 2 to 4 sentences, casual and authentic — like a real OOTD post, not a "
        "product listing.\n"
        f"- Mention the item name ({title}), the price ({price_str}), and the "
        f"platform ({platform}) naturally, each exactly once.\n"
        "- Capture the outfit's vibe in specific terms.\n"
        "- Just return the caption text, no labels or quotation marks."
    )

    response = client.chat.completions.create(
        model=_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You write fun, authentic social media captions for "
                "secondhand fashion finds.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.9,  # higher temp → captions vary for different inputs
    )
    return response.choices[0].message.content.strip()
