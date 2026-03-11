import os

from dotenv import load_dotenv
from flask import Flask, render_template, request

from services.code_review import analyze_github_repository
from services.github_service import create_issue, resolve_repo_target
from services.problem_generator import generate_problems


load_dotenv(dotenv_path=".env", override=True)

app = Flask(__name__)
app.config["GITHUB_TOKEN"] = os.getenv("GITHUB_TOKEN", "")
app.config["REPO_OWNER"] = os.getenv("REPO_OWNER", "")
app.config["REPO_NAME"] = os.getenv("REPO_NAME", "")

TOPIC_LABELS = {
    "recursion": "재귀",
    "backtracking": "백트래킹",
    "graph": "그래프",
    "bfs": "BFS",
    "dfs": "DFS",
    "dynamic programming": "동적 계획법",
    "brute force": "완전탐색",
    "binary search": "이분 탐색",
}


@app.route("/", methods=["GET", "POST"])
def index():
    github_token_set = bool(app.config["GITHUB_TOKEN"])
    repo_owner, repo_name = resolve_repo_target(
        app.config["REPO_OWNER"],
        app.config["REPO_NAME"],
    )
    topic = ""
    results = []
    analysis = None

    if request.method == "POST":
        action = request.form.get("action", "generate")
        topic = request.form.get("topic", "").strip()

        if action == "analyze":
            if not repo_owner or not repo_name:
                analysis = {
                    "analyzed_files_count": 0,
                    "detected_topics": [],
                    "weak_or_missing_topics": [],
                    "simple_review_comments": ["저장소 대상이 설정되지 않았습니다."],
                    "recommended_next_topics": [],
                    "recommended_practice_problems": [],
                }
            else:
                try:
                    analysis = analyze_github_repository(repo_owner, repo_name)
                except Exception as exc:
                    analysis = {
                        "analyzed_files_count": 0,
                        "detected_topics": [],
                        "weak_or_missing_topics": [],
                        "simple_review_comments": [str(exc)],
                        "recommended_next_topics": [],
                        "recommended_practice_problems": [],
                    }
        else:
            problems = generate_problems(topic)

            for problem in problems:
                result = {
                    "title": problem["title"],
                    "body": problem["body"],
                    "status": "생성 대기",
                    "issue_number": None,
                    "issue_url": None,
                    "error": None,
                }

                if not github_token_set:
                    result["error"] = "GITHUB_TOKEN이 설정되지 않았습니다."
                elif not repo_owner or not repo_name:
                    result["error"] = "저장소 대상이 설정되지 않았습니다."
                else:
                    try:
                        issue = create_issue(
                            repo_owner=repo_owner,
                            repo_name=repo_name,
                            title=problem["title"],
                            body=problem["body"],
                        )
                        result["status"] = "생성 완료"
                        result["issue_number"] = issue.get("number")
                        result["issue_url"] = issue.get("html_url")
                    except Exception as exc:
                        result["error"] = str(exc)

                results.append(result)

    return render_template(
        "index.html",
        github_token_set=github_token_set,
        repo_owner=repo_owner,
        repo_name=repo_name,
        repo_target=f"{repo_owner}/{repo_name}" if repo_owner and repo_name else "설정되지 않음",
        topic=topic,
        results=results,
        analysis=analysis,
        topic_labels=TOPIC_LABELS,
    )


if __name__ == "__main__":
    app.run(debug=False, use_reloader=False)
