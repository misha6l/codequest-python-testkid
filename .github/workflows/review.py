import json
import os
import urllib.request

with open("submissions/solution.py", "r") as f:
    code = f.read()

with open("rubrics/mission-2.json", "r") as f:
    rubric = json.load(f)

with open("identity.json", "r") as f:
    identity = json.load(f)

requirements = rubric["requirements"]
req_list = "\n".join([str(i+1) + ". " + r for i, r in enumerate(requirements)])

token = os.environ["GH_TOKEN"]
print("Token length: " + str(len(token)))

prompt = (
    "You are an AI code reviewer for a kids coding platform called CodeQuest. "
    "The student theme is SpongeBob. Use fun SpongeBob references in feedback.\n\n"
    "Mission: " + rubric["title"] + "\n\n"
    "Requirements:\n" + req_list + "\n\n"
    "Student code:\n" + code + "\n\n"
    "Respond ONLY with valid JSON, no markdown, no extra text:\n"
    "{\"results\": [{\"req\": \"requirement text\", \"pass\": true, \"feedback\": \"short sentence\"}], "
    "\"allPass\": true, "
    "\"message\": \"2-3 sentence SpongeBob themed message\"}"
)

payload = json.dumps({
    "model": "meta-llama-3.1-70b-instruct",
    "messages": [{"role": "user", "content": prompt}],
    "temperature": 0.3
}).encode()

req = urllib.request.Request(
    "https://models.inference.ai.azure.com/chat/completions",
    data=payload,
    method="POST",
    headers={
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json"
    }
)

with urllib.request.urlopen(req) as resp:
    ai_resp = json.loads(resp.read())

raw = ai_resp["choices"][0]["message"]["content"].strip()
raw = raw.replace("```json", "").replace("```", "").strip()
result = json.loads(raw)
print("AI review complete")

passed = result["allPass"]
lines = []

if passed:
    lines.append("## 🎉 ALL REQUIREMENTS PASSED!")
    lines.append("")
    lines.append("> " + result["message"])
    lines.append("")
else:
    lines.append("## 🤖 AI Review Complete — Not quite yet!")
    lines.append("")
    lines.append("> " + result["message"])
    lines.append("")

lines.append("### 📋 Requirements Check")
lines.append("")
for r in result["results"]:
    icon = "✅" if r["pass"] else "❌"
    lines.append(icon + " **" + r["req"] + "**")
    lines.append("   > " + r["feedback"])
    lines.append("")

if passed:
    lines.append("---")
    lines.append("### 🏅 Badge Earned: " + rubric["badge"])
    lines.append("### ⚡ +" + str(rubric["xpReward"]) + " XP added to your profile!")
    lines.append("### ⚔️ Next mission unlocked: **" + rubric["unlocks"] + "**")
    lines.append("")
    lines.append("Check your profile page to see your new badge! Your next mission Issue will open shortly.")
else:
    lines.append("---")
    lines.append("💪 Fix the ❌ items above and push your updated solution.py to try again!")
    lines.append("SpongeBob believes in you! 🧽")

comment_body = "\n".join(lines)

repo = os.environ.get("REPO")

if token and repo:
    issues_url = "https://api.github.com/repos/" + repo + "/issues?state=open&per_page=10"
    req2 = urllib.request.Request(issues_url, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    })
    try:
        with urllib.request.urlopen(req2) as resp:
            issues = json.loads(resp.read())

        issue_number = None
        for issue in issues:
            if "mission" in issue["title"].lower() or "loop" in issue["title"].lower():
                issue_number = issue["number"]
                break
        if not issue_number and issues:
            issue_number = issues[0]["number"]

        if issue_number:
            comment_url = "https://api.github.com/repos/" + repo + "/issues/" + str(issue_number) + "/comments"
            comment_data = json.dumps({"body": comment_body}).encode()
            comment_req = urllib.request.Request(
                comment_url, data=comment_data, method="POST",
                headers={
                    "Authorization": "Bearer " + token,
                    "Accept": "application/vnd.github+json",
                    "Content-Type": "application/json",
                    "X-GitHub-Api-Version": "2022-11-28"
                }
            )
            with urllib.request.urlopen(comment_req) as resp:
                print("Comment posted to issue #" + str(issue_number))

            if passed:
                close_data = json.dumps({"state": "closed"}).encode()
                close_req = urllib.request.Request(
                    "https://api.github.com/repos/" + repo + "/issues/" + str(issue_number),
                    data=close_data, method="PATCH",
                    headers={
                        "Authorization": "Bearer " + token,
                        "Accept": "application/vnd.github+json",
                        "Content-Type": "application/json",
                        "X-GitHub-Api-Version": "2022-11-28"
                    }
                )
                with urllib.request.urlopen(close_req):
                    print("Issue closed")

                next_body = (
                    "## MISSION 3 UNLOCKED: The Dictionary of Doom\n\n"
                    "> Plankton has stolen the Krabby Patty secret formula and locked it in a Python dictionary! "
                    "Write a script that stores, retrieves, and updates data using dictionaries. Stop him!\n\n"
                    "### Requirements\n"
                    "- [ ] Creates a dictionary with at least 3 key-value pairs\n"
                    "- [ ] Accesses at least one value using its key\n"
                    "- [ ] Uses a loop to iterate over the dictionary\n"
                    "- [ ] Adds or updates at least one key-value pair\n"
                    "- [ ] Uses print() to display dictionary contents\n\n"
                    "### Reward\n"
                    "- **+220 XP**\n"
                    "- **Dict Wizard Badge**\n\n"
                    "Edit submissions/solution.py and push to submit!\n\n"
                    "Good luck! Sandy is rooting for you!"
                )

                new_issue_data = json.dumps({
                    "title": "Mission 3: The Dictionary of Doom",
                    "body": next_body,
                    "labels": []
                }).encode()
                new_issue_req = urllib.request.Request(
                    "https://api.github.com/repos/" + repo + "/issues",
                    data=new_issue_data, method="POST",
                    headers={
                        "Authorization": "Bearer " + token,
                        "Accept": "application/vnd.github+json",
                        "Content-Type": "application/json",
                        "X-GitHub-Api-Version": "2022-11-28"
                    }
                )
                with urllib.request.urlopen(new_issue_req) as resp:
                    new_issue = json.loads(resp.read())
                    print("Next mission opened: #" + str(new_issue["number"]))

    except Exception as e:
        print("GitHub API error: " + str(e))

if passed:
    identity["xp"] = identity.get("xp", 0) + rubric["xpReward"]
    if rubric["badge"] not in identity.get("badges", []):
        identity.setdefault("badges", []).append(rubric["badge"])
    identity.setdefault("completedMissions", [])
    if rubric["missionId"] not in identity["completedMissions"]:
        identity["completedMissions"].append(rubric["missionId"])
    identity["currentMission"] = rubric["unlocks"]
    identity["level"] = len(identity["completedMissions"]) + 1
    with open("identity.json", "w") as f:
        json.dump(identity, f, indent=2)
    print("identity.json updated")

print("Review complete. All passed: " + str(passed))
