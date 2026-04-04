import subprocess
from rapidfuzz import process
from tools import tool
from dotenv import load_dotenv
import os

class BMOGit:

    def __init__(self):
        load_dotenv()
        result = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
        self.repo_path = result.stdout.strip()

    @tool
    def set_repo(self, repo: str):
        """
        Sets the repo path
        Args:
            repo: String used to fuzzy match with the name of the repo

        Returns:
            What the repo_path was set to

        """
        git_folders = []
        for root, dirs, files in os.walk("/home/brumeako/Projects"):
            dirs[:] = [d for d in dirs if d != ".git"]
            if ".git" in os.listdir(root):
                git_folders.append(root)

        match = process.extractOne(repo, git_folders)
        self.repo_path = match[0] if match else self.repo_path
        return f"Set the repo path to {self.repo_path}"

    @tool
    def status(self):
        """
        Runs git status
        Returns:
            Wheter the command was successful

        """
        result = subprocess.run(["git", "status"], capture_output=True, text=True, cwd=self.repo_path)
        if result.stdout:
            return result.stdout
        else:
            return result.stderr

    @tool
    def commit(self, message: str, all: bool = "Whether to commit all files or not", specific_files: list = "If not commits all files what files to commit"):
        """
        Runs git commit
        Args:
            message: The message to commit
            all: To commit all files or not
            specific_files: If you don't commit all files what files to commit

        Returns:
            Wheter the command was successful

        """
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

    @tool
    def push(self):
        """
        Runs git push
        Returns:
            Wheter the command was successful

        """
        result = subprocess.run(["git", "push"], capture_output=True, text=True, cwd=self.repo_path)
        return result.stdout or result.stderr

    @tool
    def pull(self):
        """
        Runs git pull
        Returns:
            Wheter the command was successful

        """
        result = subprocess.run(["git", "pull"], capture_output=True, text=True, cwd=self.repo_path)
        return result.stdout or result.stderr

    @tool
    def analyze_repo(self):
        """
        Looks at an entire repo and take all the code in
        Returns:

        """
        files = []
        result = subprocess.run(["fd", ".", "--type", "f", "-e", "py"], capture_output=True, text=True, cwd=self.repo_path)
        if result.stderr:
            return result.stderr
        file_paths = result.stdout.splitlines()
        for file in file_paths:
            files.append(open(file).read())

        return files

git = BMOGit()
