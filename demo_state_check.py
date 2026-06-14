"""
demo_state_check.py — proves state flows between tools by OBJECT IDENTITY.

It intercepts suggest_outfit / create_fit_card in the agent's namespace, records
exactly what they receive, and compares with `is` (not `==`). The LLM tools are
stubbed, so this runs offline with no API key and no cost — reproducible on camera.

Run:
    .venv/bin/python demo_state_check.py
"""

from unittest.mock import patch

import agent
from agent import run_agent
from utils.data_loader import get_example_wardrobe

captured = {}


def fake_suggest_outfit(new_item, wardrobe):
    captured["suggest_new_item"] = new_item            # object handed to tool 2
    return "OUTFIT_SENTINEL: hoodie + baggy jeans + sneakers"


def fake_create_fit_card(outfit, new_item):
    captured["fitcard_outfit"] = outfit                # object handed to tool 3
    captured["fitcard_new_item"] = new_item
    return "FITCARD_SENTINEL"


with patch.object(agent, "suggest_outfit", fake_suggest_outfit), \
     patch.object(agent, "create_fit_card", fake_create_fit_card):
    session = run_agent("vintage graphic tee under $30", get_example_wardrobe())

sel = session["selected_item"]
out = session["outfit_suggestion"]

print("=== selected_item flow (session -> suggest_outfit) ===")
print("session[selected_item] :", sel["title"], "| id=", id(sel))
print("arg into suggest_outfit:", captured["suggest_new_item"]["title"],
      "| id=", id(captured["suggest_new_item"]))
print("SAME OBJECT (is):", sel is captured["suggest_new_item"])
print()
print("=== selected_item flow (session -> create_fit_card) ===")
print("arg into create_fit_card:", captured["fitcard_new_item"]["title"],
      "| id=", id(captured["fitcard_new_item"]))
print("SAME OBJECT (is):", sel is captured["fitcard_new_item"])
print()
print("=== outfit_suggestion flow (suggest_outfit -> session -> create_fit_card) ===")
print("session[outfit_suggestion]:", repr(out), "| id=", id(out))
print("arg into create_fit_card  :", repr(captured["fitcard_outfit"]),
      "| id=", id(captured["fitcard_outfit"]))
print("SAME OBJECT (is):", out is captured["fitcard_outfit"])
print()
print("=== no hardcoding / re-prompt check ===")
print("outfit came from tool return? ",
      out == "OUTFIT_SENTINEL: hoodie + baggy jeans + sneakers")
print("fit_card came from tool return?",
      session["fit_card"] == "FITCARD_SENTINEL")
