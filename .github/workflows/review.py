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

    # --- 2. GitHub Models Setup (GPT-4o-mini) ---
    url = "https://models.inference.ai.azure.com/chat/completions"
    token = os.environ.get("GH_TOKEN")
    
    # Use gpt-4o-mini as it is the most reliable for the free tier
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

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # --- 3. Call AI ---
    print(f"Calling King Neptune (AI) at {model_id}...")
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            response_data = json.loads(resp.read().decode("utf-8"))
            raw_ai_text = response_data["choices"][0]["message"]["content"].strip()
            
            # Extract JSON cleanly in case of chatter
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

    # --- 5. Find and Post to the Issue ---
    repo = os.environ.get("REPO")
    gh_headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    try:
        # Get all open issues
        issues_url = f"https://api.github.com/repos/{repo}/issues?state=open"
        with urllib.request.urlopen(urllib.request.Request(issues_url, headers=gh_headers)) as resp:
            issues = json.loads(resp.read())
        
        # Search for the issue (looking for "Mission 2" or "Loop")
        issue_num = None
        for i in issues:
            title_lower = i["title"].lower()
            if "mission 2" in title_lower or "loop" in title_lower:
                issue_num = i["number"]
                break
        
        # If no specific title found, use the most recent open issue
        if not issue_num and issues:
            issue_num = issues[0]["number"]

        if issue_num:
            print(f"Found Issue #{issue_num}. Posting comment...")
            post_url = f"https://api.github.com/repos/{repo}/issues/{issue_num}/comments"
            post_data = json.dumps({"body": comment_body}).encode()
            
            post_req = urllib.request.Request(post_url, data=post_data, headers=gh_headers, method="POST")
            urllib.request.urlopen(post_req)
            print(f"Success! Feedback sent to Issue #{issue_num}")
            
            # Close issue if passed
            if passed:
                patch_url = f"https://api.github.com/repos/{repo}/issues/{issue_num}"
                patch_req = urllib.request.Request(patch_url, data=json.dumps({"state": "closed"}).encode(), headers=gh_headers, method="PATCH")
                urllib.request.urlopen(patch_req)
                print("Mission accomplished. Issue closed.")
        else:
            print("Barnacles! No open issues found to post feedback to.")

    except Exception as e:
        print(f"GitHub API Error: {e}")

if __name__ == "__main__":
    run_review()
