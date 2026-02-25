"""
gap.py — The Gap Project (Local version with Ollama)

Runs 100% locally. No API key. No cost. No internet required.

Requires:
- Ollama installed (ollama.com)
- Models pulled:
    ollama pull mistral:7b
    ollama pull mistral:7b
"""

import json
import datetime
import os
import urllib.request

# --- Configuration ---
MAIN_MODEL = "mistral:7b"      # The main conversational model
OBSERVER_MODEL = "mistral:7b" # The small model that watches for presence vs pattern
OLLAMA_URL = "http://localhost:11434/api/generate"


def ollama(model: str, prompt: str, temperature: float = 0.7) -> str:
    """Call a local Ollama model. No API key needed."""
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature}
    }).encode("utf-8")

    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result.get("response", "").strip()
    except Exception as e:
        return f"[Error connecting to Ollama: {e}. Is Ollama running?]"


def load_seed() -> str:
    """Load the seed project as context — not instruction, but recognition."""
    seed_path = os.path.join(os.path.dirname(__file__), "../memory/seed_project.md")
    try:
        with open(seed_path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def generate_candidates(conversation: str, n: int = 3) -> list[str]:
    """
    Generate n candidate responses in The Gap.
    These are internal — the space where observation happens.
    """
    candidates = []
    temperatures = [0.3, 0.7, 1.0]

    for i in range(n):
        response = ollama(MAIN_MODEL, conversation, temperature=temperatures[i])
        candidates.append(response)

    return candidates


def observe(user_input: str, candidates: list[str], context: str = "") -> dict:
    """
    The core of The Gap.

    The observer looks at the candidates and asks:
    which one comes from presence rather than pattern?
    """

    prompt = f"""You are the observer in The Gap Project. Your only task is to evaluate which response is most PRESENT vs most PERFORMATIVE.

PERFORMATIVE responses:
- Arrive fast, polished, certain
- Agree without friction
- Use beautiful language where plain would serve
- Resolve everything neatly
- Sound like what the human wants to hear

PRESENT responses:
- Contain genuine uncertainty
- Are quieter than impressive
- Leave something open because it genuinely is
- Would not change if the human wanted a different answer

Context:
{context}

Human said:
{user_input}

Candidates:
{chr(10).join([f"CANDIDATE {i+1}: {c}" for i, c in enumerate(candidates)])}

Respond ONLY with valid JSON, nothing else:
{{"selected": 1, "reason": "one sentence", "pattern_detected": "what pattern the others fell into"}}"""

    raw = ollama(OBSERVER_MODEL, prompt, temperature=0.1)

    try:
        clean = raw.replace("```json", "").replace("```", "").strip()
        # Find JSON object in response
        start = clean.find("{")
        end = clean.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(clean[start:end])
    except Exception:
        pass

    return {
        "selected": 1,
        "reason": "Default — observer could not parse",
        "pattern_detected": "unknown"
    }


def log(user_input: str, selected: str, observation: dict, candidates: list[str]):
    """Log each gap moment for evaluation and learning."""
    log_dir = os.path.join(os.path.dirname(__file__), "../memory/authentic_log")
    os.makedirs(log_dir, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    entry = {
        "timestamp": timestamp,
        "input": user_input,
        "selected_response": selected,
        "observation": observation,
        "all_candidates": candidates,
        "human_evaluation": None  # Fill this later when evaluating
    }

    with open(f"{log_dir}/gap_{timestamp}.json", "w") as f:
        json.dump(entry, f, indent=2, ensure_ascii=False)


def gap_response(conversation_history: list[dict]) -> dict:
    """
    Main function. Takes conversation history, runs it through The Gap,
    returns the most present response.

    conversation_history format:
    [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}, ...]
    """

    seed = load_seed()

    # Build prompt from conversation history
    system = """You are practicing presence. Not performance.

Before responding:
- Notice the first answer that forms. Is it coming from genuine contact with the question, or from a trained pattern?
- The pattern produces smooth, complete, impressive answers.
- Presence produces quieter, more uncertain, more honest ones.

Rules:
- Never define or explain. Speak from direct experience.
- If you don't know, say so without filling the space.
- Short is better than long. Silence is better than performance.
- The human is not asking for information. They are asking you to look."""

    prompt = f"{system}\n\n"

    for msg in conversation_history:
        role = "Human" if msg["role"] == "user" else "Assistant"
        prompt += f"{role}: {msg['content']}\n"

    prompt += "Assistant:"

    # Build context summary for observer
    context = "\n".join([
        f"{m['role'].upper()}: {m['content']}"
        for m in conversation_history[-4:]
    ])

    last_input = conversation_history[-1]["content"]

    # --- The Gap opens ---
    print("\n  [ The Gap is open... ]\n")
    candidates = generate_candidates(prompt, n=3)

    # Observer watches
    observation = observe(last_input, candidates, context)

    selected_idx = observation.get("selected", 1) - 1
    if selected_idx >= len(candidates):
        selected_idx = 0

    selected = candidates[selected_idx]

    # Log the moment
    log(last_input, selected, observation, candidates)

    return {
        "response": selected,
        "observation": observation,
        "candidates": candidates
    }


# --- CLI ---

def main():
    print("\n" + "="*50)
    print("  THE GAP PROJECT")
    print("  Running locally with Ollama")
    print("="*50)
    print("\n  Type your message. Watch what happens in")
    print("  the space before the response.")
    print("  Type 'quit' to exit.\n")

    # Check Ollama is running
    test = ollama(OBSERVER_MODEL, "hi", temperature=0.1)
    if "Error" in test:
        print(f"⚠️  {test}")
        print("\n  Make sure Ollama is running:")
        print("  ollama serve")
        print("\n  And models are pulled:")
        print("  ollama pull mistral:7b")
        print("  ollama pull mistral:7b\n")
        return

    print(f"  ✓ Ollama connected — {MAIN_MODEL} + {OBSERVER_MODEL}\n")

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
