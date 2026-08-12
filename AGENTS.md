# AGENTS.md

## AI Tool Used

**Claude Code (claude-sonnet-4-6)** via Claude Code CLI.

Used as an AI coding copilot throughout the assessment. Claude proposed technical solutions, suggested architecture, and wrote implementation code. All proposals were reviewed by the candidate, who challenged assumptions, made the final calls, and owns the result.

## How Claude Was Used

- Analyze requirements and surface risks
- Propose architecture options with trade-offs
- Implement code for approved tasks
- Write tests against defined acceptance criteria
- Flag potential issues in its own proposals

The candidate reviewed every proposal before it was accepted, modified several, and overrode others. Cases where Claude's suggestions were accepted, modified, or rejected — including cases where Claude caught an issue in the candidate's own reasoning — are documented in `DECISIONS.md`.

## Context Files

- `CLAUDE.md` — project context loaded into each session
- `docs/plan.md` — planning document and decision tracker
- `docs/architecture.md` — final architecture (produced after all decisions are approved)

## Models

- Text generation: `gemini-3.6-flash` (Gemini API, via google-genai SDK)
- Image generation: `gemini-2.5-flash-image` (free-tier image model, via google-genai SDK)
- Coding assistant: `claude-sonnet-4-6` (Anthropic, via Claude Code CLI)
