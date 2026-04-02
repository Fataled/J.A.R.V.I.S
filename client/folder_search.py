import os
import subprocess

from rapidfuzz import process

def set_repo(repo: str):
    """
    Set the working directory for the repo based of a fuzzy search from the passed string
    """
    git_folders = []
    for root, dirs, files in os.walk("/home/brumeako/Projects"):
        dirs[:] = [d for d in dirs if d != ".git"]
        if ".git" in os.listdir(root):
            git_folders.append(root)

    match = process.extractOne(repo, git_folders)
    return match[0] if match else None

print(set_repo("jarvis"))

result = subprocess.run(["fd", "main.py"], capture_output=True, text=True, cwd="/home/brumeako/")
files = result.stdout.strip().splitlines()
print(files)
