"""ChatGPT export importer.

Parses ChatGPT conversations.json exports into Cascade JSONL-compatible records.
"""

import json
from datetime import datetime, timezone
from pathlib import Path


# Keyword lists for tag inference
CODE_KEYWORDS = ["code", "python", "javascript", "programming", "debug", "api", "function", "error", "bug", "script", "html", "css", "sql", "git"]
WORK_KEYWORDS = ["meeting", "project", "deadline", "client", "presentation", "report", "strategy", "manager", "team", "stakeholder"]
HEALTH_KEYWORDS = ["health", "exercise", "diet", "sleep", "workout", "medical", "therapy", "mental", "stress", "anxiety"]
FINANCE_KEYWORDS = ["budget", "investment", "salary", "tax", "expense", "savings", "finance", "money", "cost", "price"]
LEARNING_KEYWORDS = ["learn", "course", "study", "tutorial", "book", "research", "understand", "concept", "explain"]
WRITING_KEYWORDS = ["write", "essay", "blog", "article", "draft", "edit", "proofread", "story", "content"]
PERSONAL_KEYWORDS = ["relationship", "family", "friend", "hobby", "travel", "recipe", "home", "gift", "birthday"]


def _infer_tags(title: str, user_msgs: list[str]) -> list[str]:
    """Infer tags from conversation title and first few user messages."""
    tags = ["ai_conversation"]

    # Combine title + first 3 user messages for keyword matching
    text = (title + " " + " ".join(user_msgs[:3])).lower()

    tag_map = [
        ("code", CODE_KEYWORDS),
        ("work", WORK_KEYWORDS),
        ("health", HEALTH_KEYWORDS),
        ("finance", FINANCE_KEYWORDS),
        ("learning", LEARNING_KEYWORDS),
        ("writing", WRITING_KEYWORDS),
        ("personal", PERSONAL_KEYWORDS),
    ]

    for tag, keywords in tag_map:
        if any(kw in text for kw in keywords):
            tags.append(tag)
        if len(tags) >= 4:
            break

    return tags


def _extract_messages(mapping: dict) -> tuple[list[str], list[str]]:
    """Extract user and assistant messages from a ChatGPT conversation mapping."""
    user_msgs = []
    assistant_msgs = []

    for node in mapping.values():
        msg = node.get("message")
        if not msg:
            continue

        author = msg.get("author", {})
        role = author.get("role", "")
        content = msg.get("content", {})
        parts = content.get("parts", [])

        text_parts = [str(p) for p in parts if isinstance(p, str) and p.strip()]
        if not text_parts:
            continue

        combined = " ".join(text_parts)

        if role == "user":
            user_msgs.append(combined)
        elif role == "assistant":
            assistant_msgs.append(combined)

    return user_msgs, assistant_msgs


def parse_chatgpt_export(data: list[dict]) -> list[dict]:
    """Parse a ChatGPT conversations.json export into Cascade records."""
    records = []

    for conv in data:
        conv_id = conv.get("id", "unknown")
        title = conv.get("title", "Untitled")
        create_time = conv.get("create_time")
        mapping = conv.get("mapping", {})

        if not mapping:
            continue

        user_msgs, assistant_msgs = _extract_messages(mapping)

        if not user_msgs:
            continue

        # Build condensed text
        first_user = user_msgs[0][:200] if user_msgs else ""
        first_assistant = assistant_msgs[0][:200] if assistant_msgs else "(no response)"

        text = f"[ChatGPT] {title}: Asked: {first_user} | Answer: {first_assistant}"

        # Parse timestamp
        ts = None
        if create_time:
            try:
                dt = datetime.fromtimestamp(create_time, tz=timezone.utc)
                ts = dt.isoformat()
            except (ValueError, TypeError, OSError):
                pass

        tags = _infer_tags(title, user_msgs)

        records.append({
            "id": f"chatgpt_{conv_id[:12]}",
            "ts": ts,
            "source": "ai_chat",
            "type": "conversation",
            "text": text,
            "tags": tags,
            "refs": [],
        })

    return records


def load_chatgpt_file(filepath: Path) -> list[dict]:
    """Load a ChatGPT export file and return Cascade records."""
    with open(filepath) as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("ChatGPT export must be a JSON array")

    return parse_chatgpt_export(data)
