import uvicorn
import os
import sys

def _load_dotenv():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, ".env"),
        os.path.join(os.path.dirname(base_dir), ".env"),
    ]

    for path in candidates:
        if not os.path.exists(path):
            continue

        with open(path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if not key:
                    continue
                if os.getenv(key) is None:
                    os.environ[key] = value

# Ensure the current directory is in sys.path so we can import app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

_load_dotenv()

from app.main import app

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
