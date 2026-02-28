-- Create onboarding_conversations table
create table if not exists onboarding_conversations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade not null,
  messages jsonb not null default '[]'::jsonb,
  cascade_state text not null default 'exploring',
  plan_data jsonb not null default '{}'::jsonb,
  plan_cards jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Index for finding a user's conversation
create index idx_onboarding_conversations_user_id on onboarding_conversations(user_id);

-- Only one active (non-completed) conversation per user
create unique index idx_onboarding_one_active_per_user
  on onboarding_conversations(user_id)
  where cascade_state != 'completed';

-- Auto-update updated_at
create or replace function update_updated_at_column()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger update_onboarding_conversations_updated_at
  before update on onboarding_conversations
  for each row execute function update_updated_at_column();

-- Row Level Security
alter table onboarding_conversations enable row level security;

create policy "Users can read own conversations"
  on onboarding_conversations for select
  using (auth.uid() = user_id);

create policy "Users can insert own conversations"
  on onboarding_conversations for insert
  with check (auth.uid() = user_id);

create policy "Users can update own conversations"
  on onboarding_conversations for update
  using (auth.uid() = user_id);
