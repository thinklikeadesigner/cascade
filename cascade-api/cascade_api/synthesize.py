import aiohttp

from cascade_memory import SearchResult


OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "qwen3:8b"


def build_answer_prompt(
    persona_name: str,
    core_memory: str,
    results: list[SearchResult],
    question: str,
    context: str,
) -> str:
    """Build a prompt to synthesize an answer from recall results."""
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

    return f"""You are {persona_name}'s personal memory assistant.

If the user is TELLING you something new (a fact, update, or status), acknowledge it and confirm you've noted it. Say something like "Got it, I'll remember that." Do NOT say you don't have information — they're giving you information.

If the user is ASKING a question, answer using the memories provided below. Cite which data source each piece of information comes from (e.g., calendar, email, lifelog, social, transactions, conversations). If memories don't contain the answer, say you don't have information on that.

{context_note}

Keep answers concise (2-4 sentences).

## {persona_name}'s Profile
{core_memory}

## Relevant Memories
{memories_text}

## Question
{question}

/no_think"""


async def synthesize_answer(
    persona_name: str,
    core_memory: str,
    results: list[SearchResult],
    question: str,
    context: str,
) -> str:
    """Use local Ollama model to synthesize a natural answer from recall results."""
    if not results and context == "group":
        return f"I don't have public information about that for {persona_name}."

    prompt = build_answer_prompt(persona_name, core_memory, results, question, context)

    async with aiohttp.ClientSession() as session:
        async with session.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            },
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return data["message"]["content"]
