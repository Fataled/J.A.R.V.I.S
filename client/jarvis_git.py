import os
import subprocess
from anthropic import Anthropic
from rapidfuzz import process


class JarvisGit:
    SYSTEM_PROMPT = """
    YOU ARE TO CHECK WHAT THE CLOSEST NAME OF A DIRECTORY IN A LIST OF DIRECTORIES IS TO THE GIVEN NAME AND THEN RETURN THAT DIRECTORY
    """

    def __init__(self):
        result = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
        self.repo_path = result.stdout.strip()


    def set_repo(self, repo: str):
        git_folders = []
        for root, dirs, files in os.walk("/home/brumeako/Projects"):
            dirs[:] = [d for d in dirs if d != ".git"]
            if ".git" in os.listdir(root):
                git_folders.append(root)

        match = process.extractOne(repo, git_folders)
        self.repo_path = match[0] if match else self.repo_path
        return self.repo_path


    def status(self):
        result = subprocess.run(["git", "status"], capture_output=True, text=True, cwd=self.repo_path)
        if result.stdout:
            return result.stdout
        else:
            return result.stderr

    def commit(self, message: str, all=True, specific_files: list = None):
        if all:
            subprocess.run(["git", "add", "-A"], capture_output=True, text=True, cwd=self.repo_path)
            result = subprocess.run(
                ["git", "commit", "-m", message],
                capture_output=True, text=True, cwd=self.repo_path
            )
            return result.stdout or result.stderr
        elif specific_files:
            subprocess.run(["git", "add"] + specific_files, capture_output=True, text=True, cwd=self.repo_path)
            result = subprocess.run(
                ["git", "commit", "-m", message],
                capture_output=True, text=True, cwd=self.repo_path
            )
            return result.stdout or result.stderr
        else:
            return "Didn't specify what files to commit"


    def push(self):
        result = subprocess.run(["git", "push"], capture_output=True, text=True, cwd=self.repo_path)
        return result.stdout or result.stderr


    def pull(self):
        result = subprocess.run(["git", "pull"], capture_output=True, text=True, cwd=self.repo_path)
        return result.stdout or result.stderr

git = JarvisGit()
