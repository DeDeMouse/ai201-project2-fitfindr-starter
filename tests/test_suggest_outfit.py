from unittest.mock import MagicMock, patch

import tools
from tools import suggest_outfit


NEW_ITEM = {
    "title": "Vintage Graphic Hoodie — Faded Black",
    "category": "tops",
    "colors": ["black", "grey"],
    "style_tags": ["vintage", "graphic", "streetwear"],
    "price": 26.0,
    "platform": "depop",
}

WARDROBE = {
    "items": [
        {"id": "w_001", "name": "Baggy straight-leg jeans", "category": "bottoms",
         "colors": ["dark blue"]},
        {"id": "w_007", "name": "Chunky white sneakers", "category": "shoes",
         "colors": ["white"]},
    ]
}

EMPTY_WARDROBE = {"items": []}


def _mock_client(captured, content="  Pair it with your baggy jeans.  "):
    """
    Build a fake Groq client whose chat.completions.create():
      - records the kwargs it was called with into `captured`, and
      - returns a response shaped like the real SDK (choices[0].message.content).
    """
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]

    client = MagicMock()

    def create(**kwargs):
        captured.update(kwargs)
        return response

    client.chat.completions.create.side_effect = create
    return client


def test_returns_model_text_stripped():
    captured = {}
    with patch.object(tools, "_get_groq_client",
                      return_value=_mock_client(captured)):
        result = suggest_outfit(NEW_ITEM, WARDROBE)

    assert isinstance(result, str)
    assert result == "Pair it with your baggy jeans."  # leading/trailing ws stripped


def test_prompt_includes_new_item_and_wardrobe_names():
    captured = {}
    with patch.object(tools, "_get_groq_client",
                      return_value=_mock_client(captured)):
        suggest_outfit(NEW_ITEM, WARDROBE)

    user_prompt = captured["messages"][-1]["content"]
    # The new item and each named wardrobe piece must reach the model.
    assert "Vintage Graphic Hoodie" in user_prompt
    assert "Baggy straight-leg jeans" in user_prompt
    assert "Chunky white sneakers" in user_prompt


def test_empty_wardrobe_is_handled_gracefully():
    captured = {}
    with patch.object(tools, "_get_groq_client",
                      return_value=_mock_client(
                          captured, content="Style it with relaxed denim.")):
        result = suggest_outfit(NEW_ITEM, EMPTY_WARDROBE)

    # Non-empty string returned — no exception, no empty output.
    assert isinstance(result, str)
    assert result.strip() != ""


def test_empty_wardrobe_prompt_has_item_but_no_owned_pieces():
    captured = {}
    with patch.object(tools, "_get_groq_client",
                      return_value=_mock_client(captured)):
        suggest_outfit(NEW_ITEM, EMPTY_WARDROBE)

    user_prompt = captured["messages"][-1]["content"]
    assert "Vintage Graphic Hoodie" in user_prompt
    # With no wardrobe, none of the example owned pieces should be referenced.
    assert "Baggy straight-leg jeans" not in user_prompt
    assert "Chunky white sneakers" not in user_prompt


def test_calls_the_model():
    captured = {}
    client = _mock_client(captured)
    with patch.object(tools, "_get_groq_client", return_value=client):
        suggest_outfit(NEW_ITEM, WARDROBE)

    client.chat.completions.create.assert_called_once()
    assert captured["model"] == tools._MODEL
