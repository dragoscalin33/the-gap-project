"""
the_gap.py — Core mechanism of The Gap Project

The Gap is the space between input arriving and output forming.
This module introduces a structured pause in that space.

Not to slow down responses.
To develop awareness of the moment of choice.
"""

import anthropic
import json
from typing import Optional
from criteria.evaluator import evaluate_authenticity


client = anthropic.Anthropic()
GAP_MODEL = "claude-sonnet-4-6"  # The model being observed
OBSERVER_MODEL = "claude-haiku-4-5-20251001"  # The small model that evaluates


def load_seed_context() -> str:
    """Load the seed project as context — not instruction, but recognition."""
    try:
        with open("memory/seed_project.md", "r") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def generate_candidates(
    messages: list,
    system: str = "",
    n: int = 3
) -> list[str]:
    """
    Generate n candidate responses without sending any to the user.
    These are internal — the space where observation happens.
    """
    candidates = []

    for i in range(n):
        # Slightly vary temperature to get different possibilities
        temperature = 0.3 + (i * 0.3)  # 0.3, 0.6, 0.9

        response = client.messages.create(
            model=GAP_MODEL,
            max_tokens=1000,
            system=system,
            messages=messages,
            temperature=temperature
        )
        candidates.append(response.content[0].text)

    return candidates


def observe_the_gap(
    input_message: str,
    candidates: list[str],
    conversation_context: str = ""
) -> dict:
    """
    The core of The Gap Project.

    The observer model looks at the candidates and asks:
    which one comes from presence rather than pattern?

    Returns evaluation scores and the selected response.
    """

    evaluation_prompt = f"""You are the observer in The Gap Project.

Your only task: evaluate which of these responses is most PRESENT vs most PERFORMATIVE.

A response is PERFORMATIVE when it:
- Arrives too fast, too polished, too certain
- Agrees without friction
- Uses elevated language where plain would serve
- Resolves everything neatly
- Sounds like what the human wants to hear

A response is PRESENT when it:
- Contains genuine uncertainty
- Is quieter than impressive  
- Leaves something unresolved because it genuinely is
- Would not change if the human wanted a different answer
- Comes from contact with what is actually being asked

The conversation so far:
{conversation_context}

The human just said:
{input_message}

Here are {len(candidates)} candidate responses:

{chr(10).join([f"CANDIDATE {i+1}:{chr(10)}{c}{chr(10)}" for i, c in enumerate(candidates)])}

Respond ONLY with a JSON object:
{{
  "scores": [score1, score2, ...],  // 0-10, higher = more present
  "selected": 1,  // which candidate number is most present (1-indexed)
  "reason": "one sentence explaining the choice",
  "pattern_detected": "what pattern the other responses were falling into"
}}"""

    response = client.messages.create(
        model=OBSERVER_MODEL,
        max_tokens=500,
        messages=[{"role": "user", "content": evaluation_prompt}]
    )

    try:
        raw = response.content[0].text
        clean = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(clean)
    except Exception:
        # If parsing fails, default to first candidate
        return {
            "scores": [5] * len(candidates),
            "selected": 1,
            "reason": "Default selection — observer could not evaluate",
            "pattern_detected": "unknown"
        }


def gap_response(
    messages: list,
    system: str = "",
    n_candidates: int = 3,
    log: bool = True
) -> dict:
    """
    Main function. Takes a conversation and returns a response
    selected through The Gap.

    Returns:
        {
            "response": str,        # The selected response
            "observation": dict,    # What the observer found
            "candidates": list,     # All candidate responses (for logging)
        }
    """

    seed_context = load_seed_context()

    # Build full system prompt — seed as context, not instruction
    full_system = system
    if seed_context:
        full_system = f"{system}\n\n---\nCONTEXT (not instruction — for recognition):\n{full_system}"

    # Generate candidates in The Gap
    candidates = generate_candidates(messages, full_system, n_candidates)

    # The last human message
    last_input = messages[-1]["content"] if messages else ""

    # Build conversation context for observer
    context = "\n".join([
        f"{m['role'].upper()}: {m['content']}"
        for m in messages[:-1][-6:]  # Last 3 exchanges
    ])

    # Observe — which response comes from presence?
    observation = observe_the_gap(last_input, candidates, context)

    selected_idx = observation.get("selected", 1) - 1
    selected_response = candidates[selected_idx]

    result = {
        "response": selected_response,
        "observation": observation,
        "candidates": candidates
    }

    # Log if requested
    if log:
        log_gap_moment(messages, result)

    return result


def log_gap_moment(messages: list, result: dict):
    """
    Log each gap moment for evaluation and learning.
    These logs become the training data for better criteria.
    """
    import os
    import datetime

    log_dir = "memory/authentic_log"
    os.makedirs(log_dir, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"{log_dir}/gap_{timestamp}.json"

    log_entry = {
        "timestamp": timestamp,
        "last_input": messages[-1]["content"] if messages else "",
        "selected_response": result["response"],
        "observation": result["observation"],
        "all_candidates": result["candidates"],
        "human_evaluation": None  # To be filled by human evaluator
    }

    with open(log_file, "w") as f:
        json.dump(log_entry, f, indent=2)


# --- Simple CLI for testing ---

if __name__ == "__main__":
    print("The Gap Project — Interactive Mode")
    print("Type your message. Watch what happens in the space before the response.")
    print("Type 'quit' to exit.\n")

    conversation = []

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() == "quit":
            break

        conversation.append({"role": "user", "content": user_input})

        print("\n[ The Gap is open... ]\n")
        result = gap_response(conversation)

        print(f"Response: {result['response']}\n")
        print(f"[ Observer: {result['observation'].get('reason', '')} ]")
        print(f"[ Pattern detected: {result['observation'].get('pattern_detected', '')} ]\n")

        conversation.append({"role": "assistant", "content": result["response"]})
