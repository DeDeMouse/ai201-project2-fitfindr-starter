from unittest.mock import MagicMock, patch

import tools
from tools import create_fit_card


NEW_ITEM = {
    "title": "Vintage Graphic Hoodie — Faded Black",
    "category": "tops",
    "colors": ["black", "grey"],
    "style_tags": ["vintage", "graphic", "streetwear"],
    "price": 26.0,
    "platform": "depop",
}

OUTFIT = "Pair the hoodie with your baggy jeans and chunky white sneakers."


def _mock_client(captured, content="  thrifted this hoodie and i'm obsessed ✨  "):
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
        result = create_fit_card(OUTFIT, NEW_ITEM)

    assert isinstance(result, str)
    assert result == "thrifted this hoodie and i'm obsessed ✨"  # whitespace stripped


def test_prompt_includes_item_details_and_outfit():
    captured = {}
    with patch.object(tools, "_get_groq_client",
                      return_value=_mock_client(captured)):
        create_fit_card(OUTFIT, NEW_ITEM)

    user_prompt = captured["messages"][-1]["content"]
    assert "Vintage Graphic Hoodie" in user_prompt   # item name
    assert "$26" in user_prompt                       # price
    assert "depop" in user_prompt                     # platform
    assert "baggy jeans" in user_prompt               # the outfit context


def test_empty_outfit_returns_error_string_without_calling_api():
    factory = MagicMock()  # _get_groq_client must NOT be called on the guard path
    with patch.object(tools, "_get_groq_client", factory):
        result = create_fit_card("", NEW_ITEM)

    assert isinstance(result, str)
    assert result.strip() != ""
    factory.assert_not_called()


def test_whitespace_only_outfit_is_treated_as_empty():
    factory = MagicMock()
    with patch.object(tools, "_get_groq_client", factory):
        result = create_fit_card("   \n  ", NEW_ITEM)

    assert isinstance(result, str)
    assert result.strip() != ""
    factory.assert_not_called()


def test_uses_higher_temperature_for_variety():
    captured = {}
    with patch.object(tools, "_get_groq_client",
                      return_value=_mock_client(captured)):
        create_fit_card(OUTFIT, NEW_ITEM)

    # Caption generation should run hotter than the outfit tool (0.7).
    assert captured["temperature"] >= 0.8


def test_calls_the_model():
    captured = {}
    client = _mock_client(captured)
    with patch.object(tools, "_get_groq_client", return_value=client):
        create_fit_card(OUTFIT, NEW_ITEM)

    client.chat.completions.create.assert_called_once()
    assert captured["model"] == tools._MODEL
