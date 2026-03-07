import anthropic

from cascade_memory import SearchResult


def build_answer_prompt(
    persona_name: str,
    core_memory: str,
    results: list[SearchResult],
    question: str,
    context: str,
) -> str:
    """Build a Claude prompt to synthesize an answer from recall results."""
    memories_text = ""
    for r in results:
        source = r.memory.memory_type.split("_", 1)[1] if "_" in r.memory.memory_type else "unknown"
        memories_text += f"[{source}] {r.memory.content} (similarity: {r.similarity:.2f})\n"

    if not memories_text:
        memories_text = "(no relevant memories found)"

    if context == "group":
        context_note = "You are answering in a GROUP CHAT. Only reference information from the memories provided — these have already been filtered for public safety. Speak in third person about your user."
    else:
        context_note = "You are answering in a PRIVATE DM with your user. You can be personal and direct. Speak in second person."

    return f"""You are {persona_name}'s personal memory assistant. Answer the question using ONLY the memories provided below. Cite which data source each piece of information comes from (e.g., calendar, email, lifelog, social, transactions, conversations).

{context_note}

Keep answers concise (2-4 sentences). If memories don't contain the answer, say you don't have information on that.

## {persona_name}'s Profile
{core_memory}

## Relevant Memories
{memories_text}

## Question
{question}"""


async def synthesize_answer(
    client: anthropic.AsyncAnthropic,
    persona_name: str,
    core_memory: str,
    results: list[SearchResult],
    question: str,
    context: str,
) -> str:
    """Use Claude to synthesize a natural answer from recall results."""
    if not results and context == "group":
        return f"I don't have public information about that for {persona_name}."

    prompt = build_answer_prompt(persona_name, core_memory, results, question, context)

    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text
