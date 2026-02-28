import { createClient } from "@supabase/supabase-js";

export function getSupabaseClient() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
  );
}

export async function loadConversation(supabase, userId) {
  const { data, error } = await supabase
    .from("onboarding_conversations")
    .select("*")
    .eq("user_id", userId)
    .neq("cascade_state", "completed")
    .order("created_at", { ascending: false })
    .limit(1)
    .single();

  if (error && error.code !== "PGRST116") {
    // PGRST116 = no rows found, which is fine
    console.error("Error loading conversation:", error);
  }

  return data || null;
}

export async function createConversation(supabase, userId) {
  const initialMessages = [
    {
      id: Date.now(),
      role: "assistant",
      content: "What's the big goal you're working toward? Be specific — \"launch a SaaS\" is a start, but I need to know what success looks like and when you want it done.",
      type: "text",
    },
  ];

  const { data, error } = await supabase
    .from("onboarding_conversations")
    .insert({
      user_id: userId,
      messages: initialMessages,
      cascade_state: "exploring",
      plan_data: {},
      plan_cards: [],
    })
    .select()
    .single();

  if (error) {
    // Handle race condition: unique partial index violation means another tab
    // already created the conversation. Fall back to loading it.
    if (error.code === "23505") {
      console.warn("Conversation already exists, loading it instead");
      return await loadConversation(supabase, userId);
    }
    console.error("Error creating conversation:", error);
    throw error;
  }

  return data;
}

export async function saveConversation(supabase, conversationId, { messages, cascadeState, planData, planCards }) {
  const { error } = await supabase
    .from("onboarding_conversations")
    .update({
      messages,
      cascade_state: cascadeState,
      plan_data: planData,
      plan_cards: planCards || [],
    })
    .eq("id", conversationId);

  if (error) {
    console.error("Error saving conversation:", error);
    throw error;
  }
}
