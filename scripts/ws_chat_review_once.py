import asyncio
import json
import os
import websockets

HOST = os.getenv("EXAI_WS_HOST", "127.0.0.1")
PORT = int(os.getenv("EXAI_WS_PORT", "8710"))
MODEL = os.getenv("DEFAULT_MODEL", "glm-4.5-flash")

PROMPT_TEMPLATE = (
    "Review the provided markdown for clarity, concision, and user focus. "
    "Ensure: (1) no original external-model prompts are present, (2) 5-bullet summary conveys model differences without overload, "
    "(3) Mermaid blocks are syntactically valid, (4) recommendations are actionable. "
    "Return: a) brief findings bullets, b) specific corrections (quote->fix), c) final notes. Keep it concise."
)

async def call_ws(prompt: str, model: str):
    uri = f"ws://{HOST}:{PORT}"
    async with websockets.connect(uri, max_size=20 * 1024 * 1024, ping_interval=30, ping_timeout=30) as ws:
        payload = {
            "tool": "chat",
            "args": {
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "model": model,
            }
        }
        await ws.send(json.dumps(payload))
        # Collect the first non-activity text block
        full = []
        while True:
            raw = await ws.recv()
            data = json.loads(raw)
            if isinstance(data, dict):
                # Prefer 'text' if compat layer set; else parse outputs
                if data.get("text"):
                    full.append(data["text"])  # already concatenated by server compat
                    break
                outputs = data.get("outputs") or []
                # gather any text blocks
                for o in outputs:
                    t = o.get("text")
                    if t:
                        full.append(t)
                # heuristic: stop if we saw final flag
                if data.get("final") or data.get("done"):
                    break
            else:
                # unexpected type; keep reading
                continue
        print("\n".join(full).strip())

async def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("path", help="Path to markdown file to review")
    ap.add_argument("--model", default=MODEL)
    args = ap.parse_args()

    with open(args.path, "r", encoding="utf-8") as f:
        content = f.read()

    # Compose review prompt without exposing internal prompts inside the file
    review_prompt = f"{PROMPT_TEMPLATE}\n\n---\n\nCONTENT START\n\n" + content + "\n\nCONTENT END"
    await call_ws(review_prompt, args.model)

if __name__ == "__main__":
    asyncio.run(main())

