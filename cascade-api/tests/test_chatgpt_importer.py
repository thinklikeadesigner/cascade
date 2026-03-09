"""Tests for the ChatGPT export importer."""

import pytest

from cascade_api.importers.chatgpt import parse_chatgpt_export, _infer_tags


def _make_conversation(conv_id="abc123456789", title="Test Chat", create_time=1700000000, user_msg="Hello", assistant_msg="Hi there"):
    """Helper to build a minimal ChatGPT conversation structure."""
    mapping = {}
    # System node
    mapping["sys"] = {
        "message": {
            "author": {"role": "system"},
            "content": {"parts": ["You are a helpful assistant."]},
        }
    }
    # User node
    mapping["user1"] = {
        "message": {
            "author": {"role": "user"},
            "content": {"parts": [user_msg]},
        }
    }
    # Assistant node
    if assistant_msg is not None:
        mapping["asst1"] = {
            "message": {
                "author": {"role": "assistant"},
                "content": {"parts": [assistant_msg]},
            }
        }

    return {
        "id": conv_id,
        "title": title,
        "create_time": create_time,
        "mapping": mapping,
    }


def test_parse_simple_conversation():
    data = [_make_conversation(
        conv_id="abc123456789xyz",
        title="Python help",
        user_msg="How do I read a file in Python?",
        assistant_msg="You can use open() to read files.",
    )]
    records = parse_chatgpt_export(data)
    assert len(records) == 1
    r = records[0]
    assert r["id"] == "chatgpt_abc123456789"
    assert r["source"] == "ai_chat"
    assert r["type"] == "conversation"
    assert "[ChatGPT] Python help" in r["text"]
    assert "How do I read a file" in r["text"]
    assert "open()" in r["text"]
    assert "ai_conversation" in r["tags"]
    assert r["ts"] is not None


def test_parse_empty_conversation():
    """Conversations with no user messages should be skipped."""
    data = [{
        "id": "empty123",
        "title": "Empty",
        "create_time": 1700000000,
        "mapping": {
            "sys": {
                "message": {
                    "author": {"role": "system"},
                    "content": {"parts": ["system prompt"]},
                }
            }
        },
    }]
    records = parse_chatgpt_export(data)
    assert len(records) == 0


def test_infer_tags():
    # Code-related
    tags = _infer_tags("Python debugging help", ["Fix this python error"])
    assert "ai_conversation" in tags
    assert "code" in tags

    # Health-related
    tags = _infer_tags("Workout plan", ["Create an exercise routine for me"])
    assert "health" in tags

    # Finance
    tags = _infer_tags("Budget planning", ["Help me with my monthly budget"])
    assert "finance" in tags

    # Max 4 tags
    tags = _infer_tags(
        "Python code for health budget learning writing personal",
        ["code python exercise budget study essay family"],
    )
    assert len(tags) <= 4


def test_parse_multiple_conversations():
    data = [
        _make_conversation(conv_id="conv1_xxxxxxxxx", title="Chat 1", user_msg="First question"),
        _make_conversation(conv_id="conv2_xxxxxxxxx", title="Chat 2", user_msg="Second question"),
        _make_conversation(conv_id="conv3_xxxxxxxxx", title="Chat 3", user_msg="Third question"),
    ]
    records = parse_chatgpt_export(data)
    assert len(records) == 3
    ids = [r["id"] for r in records]
    assert len(set(ids)) == 3  # All unique
    assert all(r["source"] == "ai_chat" for r in records)
