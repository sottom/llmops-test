import os
import subprocess
import logging
import ast
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)

# Ensure API Key is set as an environment variable
# For local testing, load from .env with:
# from dotenv import load_dotenv
# load_dotenv()
# client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
# For GitHub Actions, set secrets directly
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


class CodeImproverAgent:
    def improve_code(self, code_content, goal="Make this Python code more Pythonic, readable, and add type hints."):
        """Uses an LLM to suggest improvements to the given code."""
        if not client.api_key:
            logging.error("OPENAI_API_KEY environment variable not set.")
            return None

        system_prompt = f"""You are an expert Python programming assistant.
Your task is to refactor the given Python code based on the user's goal.
Goal: {goal}
Please return *only* the complete refactored Python code block.
Do not include any explanations, introductions, or markdown formatting like ```python ... ```."""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini", # Or "gpt-4" etc.
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": code_content}
                ],
                temperature=0.6, # Adjust for creativity vs determinism
            )
            improved_code = response.choices[0].message.content.strip()
            logging.info("LLM code suggestion received.")
            return improved_code
        except Exception as e:
            logging.error(f"Error calling OpenAI API: {e}")
            return None

    def validate_code(self, code_string):
        """Performs basic validation using Python's ast module."""
        try:
            ast.parse(code_string)
            logging.info("Code validation successful (AST parse).")
            return True
        except SyntaxError as e:
            logging.error(f"Code validation failed: Invalid Python syntax - {e}")
            return False
        except Exception as e:
            logging.error(f"Code validation failed with unexpected error: {e}")
            return False


class PullRequestAgent:
    def create_pr(self, file_path, improved_code, branch_name="auto-refactor-suggestions"):
        """Creates a new branch, commits changes, and opens a GitHub PR."""
        try:
            # 1. Create and checkout a new branch
            subprocess.run(["git", "checkout", "-b", branch_name], check=True, capture_output=True, text=True)
            logging.info(f"Created and checked out branch: {branch_name}")

            # 2. Overwrite the file with improved code
            with open(file_path, "w") as f:
                f.write(improved_code)
            logging.info(f"Wrote improved code to: {file_path}")

            # 3. Stage and commit
            subprocess.run(["git", "add", file_path], check=True)
            commit_message = f"Auto-refactor suggestion for {os.path.basename(file_path)}"
            subprocess.run(["git", "commit", "-m", commit_message], check=True)
            logging.info("Committed changes.")

            # 4. Push the new branch
            # Use --set-upstream to link local and remote branch easily
            subprocess.run(["git", "push", "--set-upstream", "origin", branch_name], check=True, capture_output=True, text=True)
            logging.info(f"Pushed branch {branch_name} to origin.")

            # 5. Create Pull Request using GitHub CLI
            # Assumes gh CLI is installed and authenticated in the environment (GitHub Actions handles this)
            # --fill automatically populates title and body from commit
            # --base specifies the target branch for the PR
            target_base_branch = os.getenv("GITHUB_BASE_REF", "main") # Default to main if not available (e.g. push to main)
            if not target_base_branch: # Handle case where GITHUB_BASE_REF might be empty on direct push
                 # You might want to get the default branch name differently if needed
                 target_base_branch = "main" 
                 logging.warning(f"GITHUB_BASE_REF not found, defaulting target branch to '{target_base_branch}'")


            pr_result = subprocess.run(
                ["gh", "pr", "create", "--title", commit_message, "--body", "Automated code refactoring suggestion.", "--base", target_base_branch],
                check=True, capture_output=True, text=True
            )
            pr_url = pr_result.stdout.strip()
            logging.info(f"Successfully created Pull Request: {pr_url}")
            return pr_url

        except subprocess.CalledProcessError as e:
            logging.error(f"Git or GH CLI command failed:")
            logging.error(f"Command: {' '.join(e.cmd)}")
            logging.error(f"Stderr: {e.stderr}")
            logging.error(f"Stdout: {e.stdout}")
            # Attempt to switch back to original branch on failure to avoid dirty state
            try:
                main_branch = os.getenv("GITHUB_BASE_REF", "main") # Or your main branch name
                subprocess.run(["git", "checkout", main_branch], check=False)
                subprocess.run(["git", "branch", "-D", branch_name], check=False) # Clean up failed branch
            except Exception as cleanup_e:
                logging.warning(f"Could not fully clean up git state after failure: {cleanup_e}")
            return None
        except Exception as e:
            logging.error(f"An unexpected error occurred during PR creation: {e}")
            return None