import json
import os
import urllib.request
import urllib.error

def run_review():
    # --- 1. Load Data ---
    with open("submissions/solution.py", "r") as f:
        code = f.read()
    with open("rubrics/mission-2.json", "r") as f:
        rubric = json.load(f)
    with open("identity.json", "r") as f:
        identity = json.load(f)

    # --- 2. GitHub Models Setup (GPT-4o-mini) ---
    url = "https://models.inference.ai.azure.com/chat/completions"
    token = os.environ.get("GH_TOKEN")
    model_id = "gpt-4o-mini" 

    prompt = (
        f"You are SpongeBob. Review Mission: {rubric['title']}.\n"
        f"Student code:\n{code}\n\n"
        "Respond ONLY with JSON: "
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

    # --- 3. The API Call ---
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    
    try:
        with urllib.request.urlopen(req) as resp:
            response_data = json.loads(resp.read().decode("utf-8"))
            raw_ai_text = response_data["choices"][0]["message"]["content"].strip()
            
            # Extract JSON cleanly
            start = raw_ai_text.find('{')
            end = raw_ai_text.rfind('}') + 1
            result = json.loads(raw_ai_text[start:end])
            print("AI Review Received!")
    except Exception as e:
        if hasattr(e, 'read'): print(f"API Error: {e.read().decode()}")
        else: print(f"Error: {e}")
        return

    # --- 4. Post Comment to Issue #1 ---
    repo = os.environ.get("REPO")
    passed = result.get("allPass", False)
    
    lines = [f"## {'🎉 MISSION COMPLETE!' if passed else '🤖 Keep Coding!'}"]
    lines.append(f"\n> {result['message']}\n")
    for r in result.get("results", []):
        icon = "✅" if r["pass"] else "❌"
        lines.append(f"{icon} **{r['req']}**: {r['feedback']}")
    
    comment_body = "\n".join(lines)
    comment_url = f"https://api.github.com/repos/{repo}/issues/1/comments" # Force Issue #1
    
    gh_headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    try:
        urllib.request.urlopen(urllib.request.Request(comment_url, data=json.dumps({"body": comment_body}).encode(), headers=gh_headers, method="POST"))
        print("Comment posted!")
    except Exception as e:
        print(f"GitHub Post Error: {e}")

if __name__ == "__main__":
    run_review()
