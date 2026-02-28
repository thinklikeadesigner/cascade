-- Add columns for agent conversation history
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS role text;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS content text;

-- Fix monthly_plans.targets default from array to object
-- (the agent loop treats targets as key-value pairs, not an array)
ALTER TABLE monthly_plans ALTER COLUMN targets SET DEFAULT '{}'::jsonb;
UPDATE monthly_plans SET targets = '{}'::jsonb WHERE targets = '[]'::jsonb;
