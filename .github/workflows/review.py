import json
import os
import urllib.request
import urllib.error

def run_review():
    # --- 1. Load Local Data ---
    try:
        with open("submissions/solution.py", "r") as f:
            code = f.read()
        with open("rubrics/mission-2.json", "r") as f:
            rubric = json.load(f)
        with open("identity.json", "r") as f:
            identity = json.load(f)
    except Exception as e:
        print(f"File Error: {e}")
        return

    # --- 2. GitHub Models Setup ---
    # The endpoint for GitHub Models is Azure AI compatible
    url = "https://models.inference.ai.azure.com/chat/completions"
    token = os.environ.get("GH_TOKEN")
    model_id = "azureml-meta/Llama-4-Scout-17B-16E-Instruct"

    req_list = "\n".join([f"{i+1}. {r}" for i, r in enumerate(rubric["requirements"])])
    
    prompt = (
        f"You are SpongeBob SquarePants. Review this CodeQuest mission: {rubric['title']}.\n"
        f"Requirements:\n{req_list}\n\n"
        f"Student code:\n{code}\n\n"
        "Respond ONLY with valid JSON. Do not include markdown or conversational text outside the JSON.\n"
        "JSON structure: {\"results\": [{\"req\": \"text\", \"pass\": true, \"feedback\": \"text\"}], \"allPass\": true, \"message\": \"text\"}"
    )

    payload = json.dumps({
        "messages": [
            {"role": "system", "content": "You are a coding instructor who only outputs JSON."},
            {"role": "user", "content": prompt}
        ],
        "model": model_id,
        "temperature": 0.8,
        "max_tokens": 1500
    }).encode("utf-8")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # --- 3. Call the AI ---
    print(f"Sending code to {model_id}...")
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    
    try:
        with urllib.request.urlopen(req) as resp:
            response_data = json.loads(resp.read().decode("utf-8"))
            raw_ai_text = response_data["choices"][0]["message"]["content"].strip()
            
            # Clean AI response if it wrapped it in markdown
            if "```" in raw_ai_text:
                raw_ai_text = raw_ai_text.split("```")[1].split("```")[0].replace("json", "").strip()
            
            result = json.loads(raw_ai_text)
            print("AI Review Received!")
    except urllib.error.HTTPError as e:
        # This will print the actual reason from GitHub if it's a 400 error
        error_body = e.read().decode()
        print(f"Barnacles! HTTP Error {e.code}: {error_body}")
        return
    except Exception as e:
        print(f"Parsing Error: {e}")
        return

    # --- 4. Prepare the Comment ---
    passed = result.get("allPass", False)
    status_title = "## 🎉 MISSION COMPLETE!" if passed else "## 🤖 Keep Coding, Pal!"
    
    lines = [status_title, "", f"> {result['message']}", "", "### 📋 Checklist", ""]
    for r in result.get("results", []):
        icon = "✅" if r["pass"] else "❌"
        lines.append(f"{icon} **{r['req']}**\n   > {r['feedback']}\n")

    if passed:
        lines.append(f"---\n### 🏅 Badge: {rubric['badge']}\n### ⚡ +{rubric['xpReward']} XP added!")
    else:
        lines.append("---\n💪 Fix the ❌ errors and push again!")

    comment_body = "\n".join(lines)

    # --- 5. Post to GitHub ---
    repo = os.environ.get("REPO")
    gh_headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    try:
        # Find the open issue for the student
        with urllib.request.urlopen(urllib.request.Request(f"[https://api.github.com/repos/](https://api.github.com/repos/){repo}/issues?state=open", headers=gh_headers)) as resp:
            issues = json.loads(resp.read())
            issue_num = next((i["number"] for i in issues if "mission" in i["title"].lower()), issues[0]["number"] if issues else None)

        if issue_num:
            # Post comment
            comment_url = f"[https://api.github.com/repos/](https://api.github.com/repos/){repo}/issues/{issue_num}/comments"
            urllib.request.urlopen(urllib.request.Request(comment_url, data=json.dumps({"body": comment_body}).encode(), headers=gh_headers, method="POST"))
            print(f"Comment posted on #{issue_num}")

            if passed:
                # Close the issue
                urllib.request.urlopen(urllib.request.Request(f"[https://api.github.com/repos/](https://api.github.com/repos/){repo}/issues/{issue_num}", data=json.dumps({"state": "closed"}).encode(), headers=gh_headers, method="PATCH"))
                
                # Update local identity
                identity["xp"] = identity.get("xp", 0) + rubric["xpReward"]
                if rubric["badge"] not in identity.get("badges", []):
                    identity.setdefault("badges", []).append(rubric["badge"])
                
                with open("identity.json", "w") as f:
                    json.dump(identity, f, indent=2)
                print("Progress saved to identity.json")

    except Exception as e:
        print(f"GitHub Error: {e}")

if __name__ == "__main__":
    run_review()
