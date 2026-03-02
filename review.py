import json
import os
import urllib.request
import urllib.error
import py_compile
import re

def run_review():
    # --- 1. Load Identity & Detect Current Mission Dynamically ---
    try:
        with open("identity.json", "r") as f:
            identity = json.load(f)
    except Exception as e:
        print(f"Failed to load identity.json: {e}")
        return

    current_mission = identity.get("currentMission", "python-mission-1")
    # Extract mission number from e.g. "python-mission-2" → "2"
    match = re.search(r"(\d+)$", current_mission)
    mission_num = match.group(1) if match else "1"
    rubric_path = f"rubrics/mission-{mission_num}.json"

    try:
        with open("submissions/solution.py", "r") as f:
            code = f.read()
        with open(rubric_path, "r") as f:
            rubric = json.load(f)
    except Exception as e:
        print(f"File loading error: {e}")
        return

    # --- 2. PRE-CHECK: Syntax Validation ---
    syntax_passed = True
    syntax_error_msg = ""
    try:
        py_compile.compile("submissions/solution.py", doraise=True)
    except py_compile.PyCompileError as e:
        syntax_passed = False
        syntax_error_msg = str(e).split(':', 1)[-1].strip()

    # --- 3. Setup AI Tokens ---
    ai_token = os.environ.get("AI_TOKEN")
    gh_token = os.environ.get("GH_TOKEN")
    url = "https://models.inference.ai.azure.com/chat/completions"
    model_id = "gpt-4o-mini"

    # --- 4. Logic Audit (Only if Syntax is OK) ---
    if syntax_passed:
        prompt = (
            f"You are a strict technical reviewer. Evaluate this Python code "
            f"against these MANDATORY PASS CRITERIA: {rubric['requirements']}.\n\n"
            f"STUDENT CODE:\n{code}\n\n"
            "EVALUATION RULES:\n"
            "1. If a criterion is missing, 'pass' must be false.\n"
            "2. 'allPass' is true ONLY if every single criterion is met.\n"
            "3. Note: Comments do NOT count toward the '10 lines of code' requirement.\n"
            "Respond ONLY with valid JSON:\n"
            "{\"results\": [{\"req\": \"text\", \"pass\": true, \"feedback\": \"text\"}], \"allPass\": true, \"message\": \"text\"}"
        )

        payload = json.dumps({
            "messages": [
                {"role": "system", "content": "You are a professional code auditor who outputs strictly formatted JSON feedback."},
                {"role": "user", "content": prompt}
            ],
            "model": model_id,
            "temperature": 0.0
        }).encode("utf-8")

        req = urllib.request.Request(
            url, data=payload,
            headers={"Authorization": f"Bearer {ai_token}", "Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req) as resp:
                response_data = json.loads(resp.read().decode("utf-8"))
                raw_ai_text = response_data["choices"][0]["message"]["content"].strip()
                start = raw_ai_text.find('{')
                end = raw_ai_text.rfind('}') + 1
                result = json.loads(raw_ai_text[start:end])
        except Exception as e:
            print(f"AI Error: {e}")
            return
    else:
        result = {
            "allPass": False,
            "message": f"Barnacles! Your code has a syntax error: {syntax_error_msg}",
            "results": [{"req": "Valid Python Syntax", "pass": False, "feedback": "Fix your colons or indentation!"}]
        }

    # --- 5. Format GitHub Issue Comment ---
    passed = result.get("allPass", False)
    status = "✅ PASSED" if passed else "❌ TRY AGAIN"
    comment_body = f"## {status}\n\n> {result.get('message', 'Keep going!')}\n\n"
    for r in result.get("results", []):
        icon = "✅" if r["pass"] else "❌"
        comment_body += f"{icon} **{r['req']}**: {r['feedback']}\n"

    if passed:
        comment_body += f"\n\n🗺️ **[→ View your unlocked missions on the Skill Map](https://misha6l.github.io/codequest-python-testkid/map.html)**"

    # --- 6. Write feedback.md to repo ---
    try:
        hero_name = identity.get("name", "Coder")
        feedback_lines = [
            f"# 🤖 CodeQuest AI Review — Mission {mission_num}\n",
            f"**Hero:** {hero_name}  \n",
            f"**Status:** {status}\n\n",
            f"> {result.get('message', '')}\n\n",
            "## Checklist\n\n"
        ]
        for r in result.get("results", []):
            icon = "✅" if r["pass"] else "❌"
            feedback_lines.append(f"- {icon} **{r['req']}**  \n  {r['feedback']}\n")

        if passed:
            feedback_lines.append(
                f"\n---\n\n"
                f"## 🎉 YOU PASSED!\n\n"
                f"Your new missions are unlocked. Head to your Skill Map:\n\n"
                f"👉 **[Open Skill Map](https://misha6l.github.io/codequest-python-testkid/map.html)**\n"
            )
        else:
            feedback_lines.append(
                f"\n---\n\n"
                f"Fix the ❌ items above, save your file, and sync again. You've got this! 💪\n"
            )

        with open("feedback.md", "w") as f:
            f.writelines(feedback_lines)
        print("feedback.md written.")
    except Exception as e:
        print(f"Error writing feedback.md: {e}")

    # --- 7. GitHub Issue Posting ---
    repo = os.environ.get("REPO")
    gh_headers = {
        "Authorization": f"Bearer {gh_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    try:
        issues_url = f"https://api.github.com/repos/{repo}/issues?state=all"
        with urllib.request.urlopen(urllib.request.Request(issues_url, headers=gh_headers)) as resp:
            issues = json.loads(resp.read())

        # Match issue by mission number keyword
        mission_keywords = [f"mission {mission_num}", f"mission-{mission_num}"]
        issue_num = None
        for issue in issues:
            title_lower = issue["title"].lower()
            if any(kw in title_lower for kw in mission_keywords):
                issue_num = issue["number"]
                break

        if issue_num:
            post_url = f"https://api.github.com/repos/{repo}/issues/{issue_num}/comments"
            urllib.request.urlopen(urllib.request.Request(
                post_url,
                data=json.dumps({"body": comment_body}).encode(),
                headers=gh_headers, method="POST"
            ))

            patch_url = f"https://api.github.com/repos/{repo}/issues/{issue_num}"
            new_state = "closed" if passed else "open"
            urllib.request.urlopen(urllib.request.Request(
                patch_url,
                data=json.dumps({"state": new_state}).encode(),
                headers=gh_headers, method="PATCH"
            ))

    except Exception as e:
        print(f"GitHub Error: {e}")

    # --- 8. Update Identity on Pass ---
    if passed:
        identity["xp"] = identity.get("xp", 0) + rubric.get("xpReward", 0)
        badge = rubric.get("badge", "")
        if badge and badge not in identity.get("badges", []):
            identity["badges"].append(badge)

        completed = identity.get("completedMissions", [])
        if current_mission not in completed:
            completed.append(current_mission)
        identity["completedMissions"] = completed

        # Advance to next mission number
        next_num = int(mission_num) + 1
        identity["currentMission"] = f"python-mission-{next_num}"

        with open("identity.json", "w") as f:
            json.dump(identity, f, indent=2)
        print(f"Identity updated. Mission {mission_num} complete. Next: python-mission-{next_num}")

    # --- 9. Update Dashboard Data ---
    try:
        with open("last_results.json", "w") as f:
            json.dump(result, f, indent=2)
        print("Dashboard data updated.")
    except Exception as e:
        print(f"Error updating dashboard JSON: {e}")

if __name__ == "__main__":
    run_review()
