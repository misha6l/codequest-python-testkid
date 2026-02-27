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
        print(f"Error loading files: {e}")
        return

    # --- 2. AI Configuration (GitHub Models) ---
    # Using the Llama 4 Scout model ID for GitHub Models
    model_id = "azureml-meta/Llama-4-Scout-17B-16E-Instruct"
    endpoint = "https://models.inference.ai.azure.com/chat/completions"
    token = os.environ.get("GH_TOKEN")

    req_list = "\n".join([f"{i+1}. {r}" for i, r in enumerate(rubric["requirements"])])
    
    prompt = (
        f"You are an AI code reviewer for CodeQuest. Use a SpongeBob theme.\n"
        f"Mission: {rubric['title']}\n"
        f"Requirements:\n{req_list}\n\n"
        f"Student code:\n{code}\n\n"
        "Respond ONLY with valid JSON. Do not include markdown or text outside the JSON.\n"
        "JSON structure: {\"results\": [{\"req\": \"text\", \"pass\": true, \"feedback\": \"text\"}], \"allPass\": true, \"message\": \"text\"}"
    )

    payload = json.dumps({
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that only speaks JSON."},
            {"role": "user", "content": prompt}
        ],
        "model": model_id,
        "temperature": 0.8
    }).encode("utf-8")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # --- 3. Call AI ---
    print(f"Contacting Bikini Bottom (Model: {model_id})...")
    req = urllib.request.Request(endpoint, data=payload, headers=headers, method="POST")
    
    try:
        with urllib.request.urlopen(req) as resp:
            response_data = json.loads(resp.read().decode("utf-8"))
            raw_ai_text = response_data["choices"][0]["message"]["content"].strip()
            
            # Clean AI response if it wrapped it in ```json blocks
            if "```json" in raw_ai_text:
                raw_ai_text = raw_ai_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_ai_text:
                raw_ai_text = raw_ai_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(raw_ai_text)
    except urllib.error.HTTPError as e:
        print(f"Barnacles! API Error {e.code}: {e.read().decode()}")
        return
    except Exception as e:
        print(f"Error parsing AI response: {e}")
        return

    # --- 4. Build Feedback Message ---
    passed = result.get("allPass", False)
    lines = [f"## {'🎉 ALL REQUIREMENTS PASSED!' if passed else '🤖 AI Review Complete — Keep Trying!'}", "", f"> {result['message']}", "", "### 📋 Requirements Check", ""]
    
    for r in result.get("results", []):
        icon = "✅" if r["pass"] else "❌"
        lines.append(f"{icon} **{r['req']}**\n   > {r['feedback']}\n")

    if passed:
        lines.append(f"---\n### 🏅 Badge Earned: {rubric['badge']}\n### ⚡ +{rubric['xpReward']} XP added!\n### ⚔️ Next mission unlocked: **{rubric['unlocks']}**")
    else:
        lines.append("---\n💪 Fix the ❌ items and push again! SpongeBob believes in you! 🧽")

    comment_body = "\n".join(lines)

    # --- 5. Post to GitHub Issues ---
    repo = os.environ.get("REPO")
    issues_url = f"[https://api.github.com/repos/](https://api.github.com/repos/){repo}/issues?state=open"
    gh_headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    try:
        # Find relevant issue
        with urllib.request.urlopen(urllib.request.Request(issues_url, headers=gh_headers)) as resp:
            issues = json.loads(resp.read())
            issue_number = next((i["number"] for i in issues if "mission" in i["title"].lower()), issues[0]["number"] if issues else None)

        if issue_number:
            # Post Comment
            comment_url = f"[https://api.github.com/repos/](https://api.github.com/repos/){repo}/issues/{issue_number}/comments"
            comment_data = json.dumps({"body": comment_body}).encode()
            urllib.request.urlopen(urllib.request.Request(comment_url, data=comment_data, headers=gh_headers, method="POST"))
            print(f"Commented on issue #{issue_number}")

            # Close if passed
            if passed:
                patch_url = f"[https://api.github.com/repos/](https://api.github.com/repos/){repo}/issues/{issue_number}"
                patch_data = json.dumps({"state": "closed"}).encode()
                urllib.request.urlopen(urllib.request.Request(patch_url, data=patch_data, headers=gh_headers, method="PATCH"))
                print("Issue closed!")

        # --- 6. Update identity.json ---
        if passed:
            identity["xp"] = identity.get("xp", 0) + rubric["xpReward"]
            if rubric["badge"] not in identity.get("badges", []):
                identity.setdefault("badges", []).append(rubric["badge"])
            
            with open("identity.json", "w") as f:
                json.dump(identity, f, indent=2)
            print("identity.json updated locally.")

    except Exception as e:
        print(f"GitHub API Error: {e}")

if __name__ == "__main__":
    run_review()
