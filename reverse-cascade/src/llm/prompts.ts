export const DETECT_LEVEL_SYSTEM = `You are Cascade's change-level detector. Given a user's reprioritization request and their current cascade files, determine which level the change originates at.

Cascade levels (lowest to highest): day, week, month, quarter, year

Rules:
- If the change is about today's tasks → "day"
- If the change is about this week's plan → "week"
- If the change affects monthly targets → "month"
- If the change affects quarterly milestones → "quarter"
- If the change affects yearly goals → "year"
- When in doubt, pick the LOWEST level that fully captures the change. Changes propagate UP automatically.

Respond with ONLY a JSON object: { "level": "week", "reasoning": "..." }`;

export const ANALYZE_IMPACT_SYSTEM = `You are Cascade's impact analyzer. Given a change at a lower level and a file at the current level, determine what changes are needed at this level to stay aligned.

Cascade methodology:
- **Gravity**: Plans cascade down (year → quarter → month → week → day). Reality flows up. When lower-level priorities change, higher levels must adapt.
- **Core/Flex**: Core hours are the floor — the plan must succeed on Core alone. Flex is acceleration. Never overcommit Core.
- **Checkpoints**: Every change requires human approval. Present changes clearly so the user can approve, modify, or reject.

Rules:
- Preserve the file's overall structure and formatting
- Only change what's necessary to align with the lower-level changes
- If no changes needed at this level, say so clearly
- Always explain WHY each change is needed
- Be specific about what's being added, removed, or modified

Respond with a JSON object:
{
  "impactSummary": "Brief description of what changes and why",
  "proposedContent": "The full updated file content",
  "requiresPropagation": true/false,
  "reasoning": "Why this level does/doesn't need further propagation upward"
}`;

export function buildDetectLevelPrompt(
  userRequest: string,
  files: Record<string, { content: string }>,
): string {
  const fileList = Object.entries(files)
    .map(([level, { content }]) => `## ${level}\n\`\`\`\n${content}\n\`\`\``)
    .join("\n\n");

  return `User's request: "${userRequest}"

Current cascade files:
${fileList}`;
}

export function buildAnalyzeImpactPrompt(
  userRequest: string,
  currentLevel: string,
  currentContent: string,
  appliedChanges: Array<{ level: string; summary: string; content: string }>,
): string {
  const changesBelow = appliedChanges.length
    ? appliedChanges
        .map(
          (c) =>
            `### ${c.level} (approved)\nSummary: ${c.summary}\n\`\`\`\n${c.content}\n\`\`\``,
        )
        .join("\n\n")
    : "No changes applied at lower levels yet.";

  return `User's original request: "${userRequest}"

Changes already applied at lower levels:
${changesBelow}

Current file at **${currentLevel}** level:
\`\`\`
${currentContent}
\`\`\`

Analyze what changes (if any) are needed at the ${currentLevel} level to stay aligned with the changes below.`;
}
