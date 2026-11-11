
import json
import os
import urllib.request
import urllib.error

from dotenv import load_dotenv

load_dotenv()

key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

if not key:
    raise SystemExit("No GOOGLE_API_KEY in .env")

try:
    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models?pageSize=200&key={key}"
    )

    with urllib.request.urlopen(url, timeout=20) as r:
        models = json.load(r)["models"]

except urllib.error.HTTPError as e:
    raise SystemExit(f"HTTP {e.code}: {e.read().decode()[:400]}")

names = [
    m["name"].replace("models/", "")
    for m in models
    if "generateContent" in m.get("supportedGenerationMethods", [])
]

print("Usable models:\n" + "\n".join(
    " - " + n for n in names if "gemini" in n
))
