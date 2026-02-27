import json
import os
import urllib.request
import urllib.error

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

    # --- 2. Setup Tokens ---
    ai_token = os.environ.get("AI_TOKEN") 
    gh_token = os.environ.get("GH_TOKEN")
    
    url = "https://models.inference.ai.azure.com/chat/completions"
    model_id = "gpt-4o-mini" 

    # --- 3. Ironclad Prompting ---
    # We explicitly define that these are PASS criteria to prevent the AI from 
    # thinking an 'if' statement is a violation.
    prompt = (
        f"You are a strict technical reviewer. Evaluate the following Python code "
        f"against these MANDATORY PASS CRITERIA: {rubric['requirements']}.\n\n"
        f"STUDENT CODE:\n{code}\n\n"
        "EVALUATION RULES:\n"
        "1. For each criterion, check if it is explicitly present in the code.\n"
        "2. If it is present, 'pass' is true. If missing, 'pass' is false.\n"
        "3. Do NOT invent negative constraints. If a rule says 'Uses an if statement', "
        "having one is REQUIRED for success.\n"
        "4. 'allPass' must be true ONLY if EVERY single criterion is met.\n\n"
        "Respond ONLY with valid JSON:\n"
        "{\"results\": [{\"req\": \"text\", \"pass\": true, \"feedback\": \"text\"}], \"allPass\": true, \"message\": \"text\"}"
    )

    payload = json.dumps({
        "messages": [
            {"role": "system", "content": "You are a professional code auditor who outputs strictly formatted JSON feedback."},
            {"role": "user", "content": prompt}
        ],
        "model": model_id,
        "temperature": 0.0  # Set to 0 for maximum factual accuracy
    }).encode("utf-8")

    # --- 4. Call AI ---
    print(f"Calling strict auditor at {model_id}...")
    req = urllib.request.Request(url, data=payload, headers={"Authorization": f"Bearer {ai_token}", "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            response_data = json.loads(resp.read().decode("utf-8"))
            raw_ai_text = response_data["choices"][0]["message"]["content"].strip()
            
            # Clean JSON extraction
            start = raw_ai_text.find('{')
            end = raw_ai_text.rfind('}') + 1
            result = json.loads(raw_ai_text[start:end])
            print("AI audit complete!")
    except Exception as e:
        print(f"AI Error: {e}")
        return

    # --- 5. Format Message ---
    passed = result.get("allPass", False)
    status = "✅ PASSED" if passed else "❌ TRY AGAIN"
    comment_body = f"## {status}\n\n> {result.get('message', 'Keep going!')}\n\n"
    for r in result.get("results", []):
        icon = "✅" if r["pass"] else "❌"
        comment_body += f"{icon} **{r['req']}**: {r['feedback']}\n"

    # --- 6. GitHub Posting Logic ---
    repo = os.environ.get("REPO")
    gh_headers = {
        "Authorization": f"Bearer {gh_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    try:
        issues_url = f"https://api.github.com/repos/{repo}/issues?state=all" # Check all issues
        with urllib.request.urlopen(urllib.request.Request(issues_url, headers=gh_headers)) as resp:
            issues = json.loads(resp.read())
        
        issue_num = None
        for i in issues:
            if "mission 2" in i["title"].lower() or "loop" in i["title"].lower():
                issue_num = i["number"]
                break
        
        if not issue_num and issues:
            issue_num = issues[0]["number"]

        if issue_num:
            # Post the comment
            post_url = f"https://api.github.com/repos/{repo}/issues/{issue_num}/comments"
            urllib.request.urlopen(urllib.request.Request(post_url, data=json.dumps({"body": comment_body}).encode(), headers=gh_headers, method="POST"))
            
            if passed:
                # Close the issue on pass
                patch_url = f"https://api.github.com/repos/{repo}/issues/{issue_num}"
                urllib.request.urlopen(urllib.request.Request(patch_url, data=json.dumps({"state": "closed"}).encode(), headers=gh_headers, method="PATCH"))
                
                # Update identity.json locally
                identity["xp"] += rubric.get("xpReward", 0)
                if rubric["badge"] not in identity["badges"]:
                    identity["badges"].append(rubric["badge"])
                with open("identity.json", "w") as f:
                    json.dump(identity, f, indent=2)
                print("Student profile updated.")
            else:
                # Re-open if it fails so the student sees it in their 'To Do'
                patch_url = f"https://api.github.com/repos/{repo}/issues/{issue_num}"
                urllib.request.urlopen(urllib.request.Request(patch_url, data=json.dumps({"state": "open"}).encode(), headers=gh_headers, method="PATCH"))
                print("Mission failed. Issue re-opened for corrections.")

    except Exception as e:
        print(f"GitHub API Error: {e}")

if __name__ == "__main__":
    run_review()
