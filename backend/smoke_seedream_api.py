import os
import time
from pathlib import Path

import httpx


def _load_dotenv():
    base_dir = Path(__file__).resolve().parent
    candidates = [
        base_dir / ".env",
        base_dir.parent / ".env",
    ]

    for path in candidates:
        if not path.exists():
            continue

        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and os.getenv(key) is None:
                os.environ[key] = value


def main():
    _load_dotenv()

    api_key = os.getenv("EVOLINK_API_KEY")
    base_url = (os.getenv("EVOLINK_BASE_URL") or "https://api.evolink.ai/v1").rstrip("/")
    if not api_key:
        raise SystemExit("EVOLINK_API_KEY is not set")

    model = "doubao-seedream-5.0-lite"
    payload = {
        "model": model,
        "prompt": "A minimal studio product photo of a red apple on a white background, soft shadow",
        "size": "auto",
        "quality": "2K",
        "n": 2,
        "response_format": "url",
        "output_format": "jpeg",
    }

    with httpx.Client(
        base_url=base_url,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=httpx.Timeout(60.0),
    ) as client:
        r = client.post("/images/generations", json=payload)
        r.raise_for_status()
        task = r.json()
        task_id = task.get("id")
        if not task_id:
            raise RuntimeError(f"Unexpected response: {task}")

        for _ in range(90):
            s = client.get(f"/tasks/{task_id}")
            s.raise_for_status()
            status = s.json()
            if status.get("status") in ("pending", "processing"):
                time.sleep(1)
                continue

            if status.get("status") == "failed":
                raise RuntimeError(status.get("error", {}).get("message") or "EvoLink task failed")

            if status.get("status") != "completed":
                raise RuntimeError(f"Unexpected status: {status.get('status')}")

            results = status.get("results") or []
            if not results:
                raise RuntimeError("Completed but no results")

            out_dir = Path(__file__).resolve().parent / "generated_images"
            out_dir.mkdir(parents=True, exist_ok=True)
            for i, image_url in enumerate(results[:15]):
                img = client.get(image_url)
                img.raise_for_status()
                out_path = out_dir / f"seedream_smoke_{task_id}_{i+1}.jpeg"
                out_path.write_bytes(img.content)
                print(f"ok: {out_path}")
            return

        raise TimeoutError("Timed out waiting for task completion")


if __name__ == "__main__":
    main()
