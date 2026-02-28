import json
import os
import urllib.request
import urllib.error
import py_compile

def run_review():
    # --- 1. Load Data ---
    try:
        with open("submissions/solution.py", "r") as f:
            code = f.read()
        with open("rubrics/mission-2.json", "r") as f:
            rubric = json.load(f)
        with open("identity.json", "r") as f:
            identity = json.load(f)
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

        req = urllib.request.Request(url, data=payload, headers={"Authorization": f"Bearer {ai_token}", "Content-Type": "application/json"}, method="POST")
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

    # --- 5. Format GitHub Message ---
    passed = result.get("allPass", False)
    status = "✅ PASSED" if passed else "❌ TRY AGAIN"
    comment_body = f"## {status}\n\n> {result.get('message', 'Keep going!')}\n\n"
    for r in result.get("results", []):
        icon = "✅" if r["pass"] else "❌"
        comment_body += f"{icon} **{r['req']}**: {r['feedback']}\n"

    # --- 6. GitHub Posting & Rewards ---
    repo = os.environ.get("REPO")
    gh_headers = {"Authorization": f"Bearer {gh_token}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}

    try:
        issues_url = f"https://api.github.com/repos/{repo}/issues?state=all"
        with urllib.request.urlopen(urllib.request.Request(issues_url, headers=gh_headers)) as resp:
            issues = json.loads(resp.read())
        
        issue_num = next((i["number"] for i in issues if "mission 2" in i["title"].lower() or "loop" in i["title"].lower()), None)

        if issue_num:
            post_url = f"https://api.github.com/repos/{repo}/issues/{issue_num}/comments"
            urllib.request.urlopen(urllib.request.Request(post_url, data=json.dumps({"body": comment_body}).encode(), headers=gh_headers, method="POST"))
            
            if passed:
                patch_url = f"https://api.github.com/repos/{repo}/issues/{issue_num}"
                urllib.request.urlopen(urllib.request.Request(patch_url, data=json.dumps({"state": "closed"}).encode(), headers=gh_headers, method="PATCH"))
                
                identity["xp"] += rubric.get("xpReward", 0)
                if rubric["badge"] not in identity["badges"]:
                    identity["badges"].append(rubric["badge"])
                with open("identity.json", "w") as f:
                    json.dump(identity, f, indent=2)
            else:
                patch_url = f"https://api.github.com/repos/{repo}/issues/{issue_num}"
                urllib.request.urlopen(urllib.request.Request(patch_url, data=json.dumps({"state": "open"}).encode(), headers=gh_headers, method="PATCH"))

    except Exception as e:
        print(f"GitHub Error: {e}")

    # --- 7. NEW: Update Dashboard Data (CRITICAL) ---
    # This writes the AI results to the file the website actually reads.
    try:
        with open("last_results.json", "w") as f:
            json.dump(result, f, indent=2)
        print("Dashboard data updated successfully.")
    except Exception as e:
        print(f"Error updating dashboard JSON: {e}")

if __name__ == "__main__":
    run_review()
