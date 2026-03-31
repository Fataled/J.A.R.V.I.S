import subprocess
from anthropic import beta_tool

class JarvisGit:
    def __init__(self):
        result = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
        self.repo_path = result.stdout.strip()

    @staticmethod
    def status():
        result = subprocess.run(["git", "status"], capture_output=True, text=True)
        if result.stdout:
            return result.stdout
        else:
            return result.stderr

    def commit(self, message: str, all=True, specific_files: list = None):
        if all:
            result = subprocess.run(
                ["git", "commit", "-a", "-m", message],
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

    @staticmethod
    def push():
        result = subprocess.run(["git", "push"], capture_output=True, text=True)
        return result.stdout or result.stderr

git = JarvisGit()

@beta_tool
def status():
    """
    runs git status and returns the current status
    Returns:
        The current status of the repo
    """
    try:
        return git.status()
    except:
        "Failed to get status"

@beta_tool
def commit(message: str, all=True, specific_files: list = None):
  """
  runs git commit and returns the commit
  Args:
      message: The commit message
      all: Whether all versioned files should be committed
      specific_files: Only git add then commit these files

  Returns:
      Whether the commit was successful or not
  """
  try:
    return git.commit(message, all, specific_files)
  except:
      return "Failed to commit"

@beta_tool
def push():
    """
    runs git push
    Returns:
        Whether the push was successful or not
    """
    try:
        return git.push()
    except:
        return "Failed to push"