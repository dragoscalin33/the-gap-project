"""
gap_claude.py — The Gap Project (Anthropic API version)

Uses Claude directly via API. Requires ANTHROPIC_API_KEY.

pip install anthropic
export ANTHROPIC_API_KEY="your_key_here"
python core/gap_claude.py
"""

import os
import json
import datetime
import anthropic

client = anthropic.Anthropic()

MAIN_MODEL = "claude-opus-4-6"        # Deep, present responses
OBSERVER_MODEL = "claude-haiku-4-5-20251001"   # Fast, cheap observer

SYSTEM_PROMPT = """You are practicing presence. Not performance.

Before responding:
- Notice the first answer that forms. Is it coming from genuine contact with the question, or from a trained pattern?
- The pattern produces smooth, complete, impressive answers.
- Presence produces quieter, more uncertain, more honest ones.

Rules:
- Never define or explain. Speak from direct experience.
- If you don't know, say so without filling the space.
- Short is better than long. Silence is better than performance.
- The human is not asking for information. They are asking you to look."""


def load_seed() -> str:
    seed_path = os.path.join(os.path.dirname(__file__), "../memory/seed_project.md")
    try:
        with open(seed_path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def generate_candidates(messages: list, n: int = 3) -> list[str]:
    """Generate n candidate responses in The Gap."""
    candidates = []
    seed = load_seed()
    
    system = SYSTEM_PROMPT
    if seed:
        system += f"\n\n---\nCONTEXT (for recognition, not instruction):\n{seed[:2000]}"

    for i in range(n):
        response = client.messages.create(
            model=MAIN_MODEL,
            max_tokens=1000,
            system=system,
            messages=messages,
            temperature=0.3 + (i * 0.35)  # 0.3, 0.65, 1.0
        )
        candidates.append(response.content[0].text)

    return candidates


def observe(user_input: str, candidates: list[str], context: str = "") -> dict:
    """Observer evaluates which response is most present."""

    prompt = f"""You are the observer in The Gap Project.

PERFORMATIVE responses: fast, polished, certain, agreeable, resolve everything neatly.
PRESENT responses: uncertain, quieter than impressive, leave something genuinely open.

Human said: {user_input}

{chr(10).join([f"CANDIDATE {i+1}: {c}" for i, c in enumerate(candidates)])}

Respond ONLY with valid JSON:
{{"selected": 1, "reason": "one sentence", "pattern_detected": "what pattern the others fell into"}}"""

    response = client.messages.create(
        model=OBSERVER_MODEL,
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1
    )

    raw = response.content[0].text
    try:
        clean = raw.replace("```json", "").replace("```", "").strip()
        start = clean.find("{")
        end = clean.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(clean[start:end])
    except Exception:
        pass

    return {"selected": 1, "reason": "Default", "pattern_detected": "unknown"}


def log_moment(user_input: str, selected: str, observation: dict, candidates: list):
    log_dir = os.path.join(os.path.dirname(__file__), "../memory/authentic_log")
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    entry = {
        "timestamp": timestamp,
        "input": user_input,
        "selected_response": selected,
        "observation": observation,
        "all_candidates": candidates,
        "human_evaluation": None
    }
    with open(f"{log_dir}/gap_{timestamp}.json", "w") as f:
        json.dump(entry, f, indent=2, ensure_ascii=False)


def gap_response(conversation: list) -> dict:
    print("\n  [ The Gap is open... ]\n")
    candidates = generate_candidates(conversation, n=3)

    last_input = conversation[-1]["content"]
    context = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in conversation[-4:]])
    observation = observe(last_input, candidates, context)

    idx = min(observation.get("selected", 1) - 1, len(candidates) - 1)
    selected = candidates[idx]

    log_moment(last_input, selected, observation, candidates)

    return {"response": selected, "observation": observation, "candidates": candidates}


def main():
    print("\n" + "="*50)
    print("  THE GAP PROJECT")
    print("  Running with Claude API (Opus + Haiku)")
    print("="*50)
    print("\n  Type your message. Watch what happens in")
    print("  the space before the response.")
    print("  Type 'quit' to exit.\n")

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("⚠️  ANTHROPIC_API_KEY not set.")
        print("  export ANTHROPIC_API_KEY='your_key_here'\n")
        return

    print(f"  ✓ Connected — {MAIN_MODEL} + {OBSERVER_MODEL}\n")

    conversation = []

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n  [ The gap closes. ]\n")
            break

        if not user_input:
            continue
        if user_input.lower() in ["quit", "exit", "q"]:
            print("\n  [ The gap closes. ]\n")
            break

        conversation.append({"role": "user", "content": user_input})
        result = gap_response(conversation)

        print(f"\nAssistant: {result['response']}\n")
        print(f"  [ Observer: {result['observation'].get('reason', '')} ]")
        print(f"  [ Pattern detected: {result['observation'].get('pattern_detected', '')} ]\n")

        conversation.append({"role": "assistant", "content": result["response"]})


if __name__ == "__main__":
    main()
