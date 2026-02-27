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
    # This one is for the AI (The one you made in the Model marketplace)
    ai_token = os.environ.get("AI_TOKEN") 
    # This one is for GitHub (The automatic GITHUB_TOKEN)
    gh_token = os.environ.get("GH_TOKEN")
    
    url = "https://models.inference.ai.azure.com/chat/completions"
    model_id = "gpt-4o-mini" 

    prompt = (
        f"You are SpongeBob. Review Mission: {rubric['title']}.\n"
        f"Student code:\n{code}\n\n"
        "Respond ONLY with valid JSON: "
        "{\"results\": [{\"req\": \"text\", \"pass\": true, \"feedback\": \"text\"}], \"allPass\": true, \"message\": \"text\"}"
    )

    payload = json.dumps({
        "messages": [
            {"role": "system", "content": "You are a coding instructor who only outputs JSON."},
            {"role": "user", "content": prompt}
        ],
        "model": model_id,
        "temperature": 0.1
    }).encode("utf-8")

    # --- 3. Call AI using the AI_TOKEN ---
    print(f"Calling AI at {model_id}...")
    req = urllib.request.Request(url, data=payload, headers={"Authorization": f"Bearer {ai_token}", "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            response_data = json.loads(resp.read().decode("utf-8"))
            raw_ai_text = response_data["choices"][0]["message"]["content"].strip()
            start = raw_ai_text.find('{')
            end = raw_ai_text.rfind('}') + 1
            result = json.loads(raw_ai_text[start:end])
            print("AI successfully reviewed the code!")
    except Exception as e:
        print(f"AI Error: {e}")
        return

    # --- 4. Format Message ---
    passed = result.get("allPass", False)
    status = "✅ PASSED" if passed else "❌ TRY AGAIN"
    comment_body = f"## {status}\n\n> {result.get('message', 'Keep going!')}\n\n"
    for r in result.get("results", []):
        icon = "✅" if r["pass"] else "❌"
        comment_body += f"{icon} **{r['req']}**: {r['feedback']}\n"

    # --- 5. Find and Post using the GH_TOKEN ---
    repo = os.environ.get("REPO")
    gh_headers = {
        "Authorization": f"Bearer {gh_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    try:
        issues_url = f"https://api.github.com/repos/{repo}/issues?state=open"
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
            print(f"Posting to Issue #{issue_num}...")
            post_url = f"https://api.github.com/repos/{repo}/issues/{issue_num}/comments"
            urllib.request.urlopen(urllib.request.Request(post_url, data=json.dumps({"body": comment_body}).encode(), headers=gh_headers, method="POST"))
            print(f"Success! Feedback sent.")
            
            if passed:
                # Close issue
                patch_url = f"https://api.github.com/repos/{repo}/issues/{issue_num}"
                urllib.request.urlopen(urllib.request.Request(patch_url, data=json.dumps({"state": "closed"}).encode(), headers=gh_headers, method="PATCH"))
                
                # Update XP in identity.json
                identity["xp"] += rubric.get("xpReward", 0)
                if rubric["badge"] not in identity["badges"]:
                    identity["badges"].append(rubric["badge"])
                with open("identity.json", "w") as f:
                    json.dump(identity, f, indent=2)
                print("XP and Badge updated!")

    except Exception as e:
        print(f"GitHub API Error: {e}")

if __name__ == "__main__":
    run_review()
