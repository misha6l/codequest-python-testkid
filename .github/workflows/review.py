import json
import os
import urllib.request

# ── Load files ──
with open("submissions/solution.py", "r") as f:
    code = f.read()

with open("rubrics/mission-2.json", "r") as f:
    rubric = json.load(f)

with open("identity.json", "r") as f:
    identity = json.load(f)

requirements = rubric["requirements"]
req_list = "\n".join([f"{i+1}. {r}" for i, r in enumerate(requirements)])

# ── Call Groq ──
groq_key = os.environ["GROQ_API_KEY"]
print(f"Key length: {len(groq_key)}")

prompt = f"""You are an AI code reviewer for a kids coding platform called CodeQuest.
The student's theme is SpongeBob SquarePants — use fun SpongeBob references in your feedback.

A student submitted Python code for mission: "{rubric['title']}"

Check if the code meets ALL of these requirements:
{req_list}

Student's code:
```python
