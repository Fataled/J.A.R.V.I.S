import os
from rapidfuzz import process

def set_repo(repo: str):
    git_folders = []
    for root, dirs, files in os.walk("/home/brumeako/Projects"):
        dirs[:] = [d for d in dirs if d != ".git"]
        if ".git" in os.listdir(root):
            git_folders.append(root)

    match = process.extractOne(repo, git_folders)
    return match[0] if match else None

print(set_repo("intell"))
