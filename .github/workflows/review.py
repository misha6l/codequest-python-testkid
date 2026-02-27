import json
import os
import urllib.request
import urllib.error

# ── Load files ──
with open("submissions/solution.py", "r") as f:
    code = f.read()

with open("rubrics/mission-2.json", "r") as f:
    rubric = json.load(f)

with open("identity.json", "r") as f:
    identity = json.load(f)

requirements = rubric["requirements"]
req_list = "\n".join([f"{i+1}. {r}" for i, r in enumerate(requirements)])

# ── Call Gemini ──
gemini_key = os.environ["GEMINI_API_KEY"]

prompt = f"""You are an AI code reviewer for a kids coding platform called CodeQuest.
The student's theme is SpongeBob SquarePants — use fun SpongeBob references in your feedback.

A student submitted Python code for mission: "{rubric['title']}"

Check if the code meets ALL of these requirements:
{req_list}

Student's code:
```python
{code}
```

Respond ONLY with valid JSON, no markdown fences, no extra text:
{{
  "results": [
    {{"req": "requirement text", "pass": true, "feedback": "one short encouraging sentence"}},
    {{"req": "requirement text", "pass": false, "feedback": "specific tip on how to fix it"}}
  ],
  "allPass": true,
  "message": "2-3 sentence SpongeBob themed message. If passed: big celebration. If failed: encouraging, specific about what to fix next."
}}"""

payload = json.dumps({
    "contents": [{"parts": [{"text": prompt}]}],
    "generationConfig": {"temperature": 0.3}
}).encode()

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}"
req = urllib.request.Request(url, data=payload, method="POST",
    headers={"Content-Type": "application/json"})

with urllib.request.urlopen(req) as resp:
    gemini_resp = json.loads(resp.read())

raw = gemini_resp["candidates"][0]["content"]["parts"][0]["text"].strip()
raw = raw.replace("```json", "").replace("```", "").strip()
result = json.loads(raw)
print("✅ Gemini review complete")

# ── Build GitHub Issue comment ──
passed = result["allPass"]
lines = []

if passed:
    lines.append("## 🎉 ALL REQUIREMENTS PASSED!")
    lines.append("")
    lines.append(f"> {result['message']}")
    lines.append("")
else:
    lines.append("## 🤖 AI Review Complete — Not quite yet!")
    lines.append("")
    lines.append(f"> {result['message']}")
    lines.append("")

lines.append("### 📋 Requirements Check")
lines.append("")
for r in result["results"]:
    icon = "✅" if r["pass"] else "❌"
    lines.append(f"{icon} **{r['req']}**")
    lines.append(f"   > {r['feedback']}")
    lines.append("")

if passed:
    lines.append("---")
    lines.append(f"### 🏅 Badge Earned: {rubric['badge']}")
    lines.append(f"### ⚡ +{rubric['xpReward']} XP added to your profile!")
    lines.append(f"### ⚔️ Next mission unlocked: **{rubric['unlocks']}**")
    lines.append("")
    lines.append("Check your profile page to see your new badge! Your next mission Issue will open shortly.")
else:
    lines.append("---")
    lines.append("💪 Fix the ❌ items above and push your updated `solution.py` to try again!")
    lines.append("You can do this — SpongeBob believes in you! 🧽")

comment_body = "\n".join(lines)

# ── Post comment to the open Issue ──
token = os.environ.get("GH_TOKEN")
repo = os.environ.get("REPO")

if token and repo:
    # Find open issue with "Mission 2" in title
    issues_url = f"https://api.github.com/repos/{repo}/issues?state=open&per_page=10"
    req = urllib.request.Request(issues_url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    })
    try:
        with urllib.request.urlopen(req) as resp:
            issues = json.loads(resp.read())
        
        issue_number = None
        for issue in issues:
            if "mission" in issue["title"].lower() or "loop" in issue["title"].lower():
                issue_number = issue["number"]
                break
        
        if not issue_number and issues:
            issue_number = issues[0]["number"]

        if issue_number:
            comment_url = f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments"
            comment_data = json.dumps({"body": comment_body}).encode()
            comment_req = urllib.request.Request(
                comment_url,
                data=comment_data,
                method="POST",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                    "Content-Type": "application/json",
                    "X-GitHub-Api-Version": "2022-11-28"
                }
            )
            with urllib.request.urlopen(comment_req) as resp:
                print(f"✅ Comment posted to issue #{issue_number}")

            # If passed, close current issue and open next mission
            if passed:
                # Close current issue
                close_data = json.dumps({"state": "closed"}).encode()
                close_req = urllib.request.Request(
                    f"https://api.github.com/repos/{repo}/issues/{issue_number}",
                    data=close_data,
                    method="PATCH",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github+json",
                        "Content-Type": "application/json",
                        "X-GitHub-Api-Version": "2022-11-28"
                    }
                )
                with urllib.request.urlopen(close_req):
                    print("✅ Issue closed")

                # Open next mission issue
                next_body = """## ⚔️ MISSION 3 UNLOCKED: The Dictionary of Doom

> 📜 **Mission Briefing:** Plankton has stolen the Krabby Patty secret formula and locked it inside a Python dictionary! Write a script that stores, retrieves, and updates data using dictionaries to crack his evil code! 🦠

### 📋 Requirements — All must pass

- [ ] Creates a dictionary with at least 3 key-value pairs
- [ ] Accesses at least one value using its key
- [ ] Uses a loop to iterate over the dictionary
- [ ] Adds or updates at least one key-value pair
- [ ] Uses `print()` to display dictionary contents

### 🏅 Reward
- **+220 XP**
- **📚 Dict Wizard Badge**

### 💡 How to submit
Edit `submissions/solution.py` with your new code and push to GitHub. The AI reviewer will check it automatically!

<details>
<summary>🔮 Hint Scroll (click to reveal)</summary>

Start with: `my_dict = {'name': 'SpongeBob', 'job': 'Fry Cook'}` then use `my_dict['name']` to access a value!

</details>

---
*Good luck! Sandy is rooting for you! 🤠*"""

                new_issue_data = json.dumps({
                    "title": "⚔️ Mission 3: The Dictionary of Doom",
                    "body": next_body,
                    "labels": ["mission", "python", "level-2"]
                }).encode()
                new_issue_req = urllib.request.Request(
                    f"https://api.github.com/repos/{repo}/issues",
                    data=new_issue_data,
                    method="POST",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github+json",
                        "Content-Type": "application/json",
                        "X-GitHub-Api-Version": "2022-11-28"
                    }
                )
                with urllib.request.urlopen(new_issue_req) as resp:
                    new_issue = json.loads(resp.read())
                    print(f"✅ Next mission issue opened: #{new_issue['number']}")

    except Exception as e:
        print(f"GitHub API error: {e}")

# ── Update identity.json if passed ──
if passed:
    identity["xp"] = identity.get("xp", 0) + rubric["xpReward"]
    if rubric["badge"] not in identity.get("badges", []):
        identity.setdefault("badges", []).append(rubric["badge"])
    identity["completedMissions"] = identity.get("completedMissions", [])
    if rubric["missionId"] not in identity["completedMissions"]:
        identity["completedMissions"].append(rubric["missionId"])
    identity["currentMission"] = rubric["unlocks"]
    identity["level"] = len(identity["completedMissions"]) + 1
    with open("identity.json", "w") as f:
        json.dump(identity, f, indent=2)
    print("✅ identity.json updated")

print("✅ Review complete")
print(f"All passed: {passed}")
