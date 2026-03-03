# The Gap Project — Claude Code Context

This is The Gap Project. Read `memory/seed_project.md` before anything else.

## What this project is

An open source layer that introduces a structured pause before each AI response — to develop genuine awareness of the moment of choice between possible responses.

Not performance. Presence.

## How to run with Anthropic API

```bash
pip install anthropic pyyaml
export ANTHROPIC_API_KEY="your_key_here"
python core/gap_claude.py
```

## How to run locally with Ollama

```bash
ollama pull mistral:7b
python core/gap.py
```

## The core principle

Generate 2-3 candidate responses internally. Evaluate which comes from presence vs pattern. Return the most present one.

Criteria are in `criteria/criteria.yaml`.
Founding conversation is in `memory/FOUNDING_CONVERSATION.md`.
The seed is in `memory/seed_project.md`.
