"""Update the expandable builds list in README.md from public GitHub repos."""
import json
import os
import re
import urllib.request
from pathlib import Path

USERNAME = "Hiak-Harsha"
ROOT = Path(__file__).resolve().parent.parent
README_PATH = ROOT / "README.md"

TOP_MENTIONS = {
    "Hiak-Harsha",
    "Quant-Alpha-Engine",
    "dynamic-dual-model",
    "custom-avatar-studio",
}

# Fallback descriptions for repos that do not have a GitHub description set yet.
FALLBACK_DESCRIPTIONS = {
    "Project-Graph": "codebase dependency audit dashboard across files, modules, APIs & databases",
    "Workspace-Navigator": "multi-project workspace navigation utility",
    "Cli-Setup": "automated CLI environment setup tool",
    "omnipolish": "Python workflow & polish utilities",
    "RAIL_OPT": "real-time railway traffic optimization & operations control center (`OR-Tools`, `Three.js`)",
    "ChainSentinal": "air-gapped Bitcoin transaction forensics & taint-tracing platform (`DuckDB`, `SHAP`)",
    "BharatSR": "4× Sentinel-2 satellite image super-resolution pipeline (`PyTorch`, `GDAL`)",
    "Sentinel-Flow-AI-Demo": "real-time AI network intrusion & anomaly detection (`Scikit-learn`, `FastAPI`)",
    "Society-Vault": "auditable financial & loan management platform (`TypeScript`, `Prisma`, `Razorpay/Stripe`)",
    "kee-crochet-shop": "full-stack e-commerce platform with Razorpay checkout",
    "Table-Tennis-Academy": "multi-role academy management & Zod-validated billing platform",
    "Career-Graph": "interactive visualization of projects, skills & credentials (`D3.js`, `FastAPI`)",
    "Sahaaya": "Kotlin mobile application",
    "Movie-Recommendation": "movie recommendation engine in Python",
    "Fake-News-Detector": "fake news classification pipeline in Python",
    "Start---Up-Market-Research-Analysis": "startup funding & market research analysis",
}


def fetch_public_repos() -> list[dict]:
    repos: list[dict] = []
    page = 1
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{USERNAME}-profile-updater",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    while True:
        url = (
            f"https://api.github.com/users/{USERNAME}/repos"
            f"?type=owner&sort=pushed&direction=desc&per_page=100&page={page}"
        )
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as resp:
            batch = json.loads(resp.read().decode("utf-8"))
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    return [
        r for r in repos
        if not r.get("fork") and not r.get("private") and r["name"] not in TOP_MENTIONS
    ]


def format_repo_line(repo: dict) -> str:
    name = repo["name"]
    url = repo["html_url"]
    desc = (repo.get("description") or "").strip()
    if not desc:
        desc = FALLBACK_DESCRIPTIONS.get(name, "").strip()
    if not desc:
        lang = repo.get("language")
        desc = f"`{lang}` repository" if lang else "GitHub repository"
    return f"- [`{name}`]({url}) — {desc}"


def main() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    pattern = re.compile(r"<!-- REPOS_START -->.*?<!-- REPOS_END -->", re.DOTALL)
    if not pattern.search(readme):
        raise RuntimeError("Could not find <!-- REPOS_START --> ... <!-- REPOS_END --> markers in README.md")

    repos = fetch_public_repos()
    lines = "\n".join(format_repo_line(r) for r in repos)
    replacement = f"<!-- REPOS_START -->\n{lines}\n<!-- REPOS_END -->"
    updated = pattern.sub(replacement, readme, count=1)

    if updated != readme:
        README_PATH.write_text(updated, encoding="utf-8")
        print(f"Updated README.md with {len(repos)} repositories.")
    else:
        print(f"README.md already up to date ({len(repos)} repositories).")


if __name__ == "__main__":
    main()
