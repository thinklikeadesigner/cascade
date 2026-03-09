"""Ingest existing Cascade data from Supabase into the memory system."""

import logging
from supabase import Client as SupabaseClient

from cascade_memory import MemoryClient

logger = logging.getLogger(__name__)


async def ingest_from_supabase(
    client: MemoryClient,
    supabase: SupabaseClient,
    tenant_id: str,
    memory_tenant: str | None = None,
) -> dict:
    """Pull goals, tasks, adaptations, tracker entries, and conversations
    from Supabase and save them as memories.

    Args:
        tenant_id: The Supabase UUID to query data from.
        memory_tenant: The memory system tenant to save into (defaults to tenant_id).
    """
    tenant = client.for_tenant(memory_tenant or tenant_id)
    stats = {"goals": 0, "tasks": 0, "adaptations": 0, "tracker": 0, "conversations": 0, "links": 0}

    # Goals — track IDs for linking tasks back to goals
    goal_memory_ids: dict[str, str] = {}  # supabase goal id -> memory id
    goals = supabase.table("goals").select("*").eq("tenant_id", tenant_id).execute()
    for g in goals.data or []:
        text = f"Goal: {g['title']}"
        if g.get("description"):
            text += f" — {g['description']}"
        if g.get("success_criteria"):
            text += f" (success: {g['success_criteria']})"
        if g.get("target_date"):
            text += f" [due: {g['target_date']}]"
        text += f" [status: {g.get('status', 'active')}]"
        mem_id = await tenant.save(content=text, memory_type="goal_context", tags=["goal", g.get("status", "active")])
        goal_memory_ids[g["id"]] = mem_id
        stats["goals"] += 1

    # Tasks (recent — last 4 weeks)
    tasks = (
        supabase.table("tasks")
        .select("*")
        .eq("tenant_id", tenant_id)
        .order("week_start", desc=True)
        .limit(100)
        .execute()
    )
    for t in tasks.data or []:
        status = "completed" if t.get("completed") else "incomplete"
        text = f"Task ({t.get('category', 'core')}): {t['title']} [{status}]"
        if t.get("scheduled_day"):
            text += f" [scheduled: {t['scheduled_day']}]"
        task_mem_id = await tenant.save(content=text, memory_type="fact", tags=["task", t.get("category", "core"), status])
        stats["tasks"] += 1

        # Link task to its goal with part_of
        goal_id = t.get("goal_id")
        if goal_id and goal_id in goal_memory_ids:
            await tenant.link(task_mem_id, goal_memory_ids[goal_id], "part_of")
            stats["links"] += 1

    # Adaptations
    adaptations = supabase.table("adaptations").select("*").eq("tenant_id", tenant_id).execute()
    for a in adaptations.data or []:
        text = f"Pattern ({a['pattern_type']}): {a['description']}"
        approved = "approved" if a.get("approved") else "pending"
        await tenant.save(content=text, memory_type="pattern", tags=["adaptation", a["pattern_type"], approved])
        stats["adaptations"] += 1

    # Tracker entries (recent)
    tracker = (
        supabase.table("tracker_entries")
        .select("*")
        .eq("tenant_id", tenant_id)
        .order("date", desc=True)
        .limit(30)
        .execute()
    )
    for entry in tracker.data or []:
        parts = [f"Tracker {entry['date']}:"]
        for key in ["outreach_sent", "conversations", "new_clients", "features_shipped", "content_published"]:
            val = entry.get(key)
            if val and val > 0:
                parts.append(f"{key.replace('_', ' ')}={val}")
        if entry.get("mrr"):
            parts.append(f"MRR=${entry['mrr']}")
        if entry.get("energy_level"):
            parts.append(f"energy={entry['energy_level']}/5")
        if entry.get("notes"):
            parts.append(f"notes: {entry['notes']}")
        if len(parts) > 1:
            await tenant.save(content=" | ".join(parts), memory_type="fact", tags=["tracker", "daily"])
            stats["tracker"] += 1

    # Conversations (recent, non-agent-history)
    convos = (
        supabase.table("conversations")
        .select("*")
        .eq("tenant_id", tenant_id)
        .neq("source", "agent_history")
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )
    for c in convos.data or []:
        if c.get("raw_text"):
            await tenant.save(
                content=c["raw_text"][:500],
                memory_type="fact",
                tags=["conversation", c.get("source", "unknown")],
            )
            stats["conversations"] += 1

    # Auto-link: connect adaptations to related goals via similarity search
    all_saved = []  # collect all memory IDs for batch linking later if needed
    mem_tenant = memory_tenant or tenant_id
    for goal_supa_id, goal_mem_id in goal_memory_ids.items():
        try:
            # Find the goal text to search for related memories
            goal_data = next((g for g in (goals.data or []) if g["id"] == goal_supa_id), None)
            if goal_data:
                related = await tenant.recall(goal_data["title"], count=5, threshold=0.35)
                for r in related:
                    if r.memory.id != goal_mem_id:
                        await tenant.link(goal_mem_id, r.memory.id, "related")
                        stats["links"] += 1
        except Exception as e:
            logger.warning(f"Auto-linking goal failed: {e}")

    logger.info(f"Supabase ingest for {tenant_id}: {stats}")
    return stats
