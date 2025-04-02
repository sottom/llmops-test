import mlflow
import os
import logging
from agents import CodeImproverAgent, PullRequestAgent
import time

logging.basicConfig(level=logging.INFO)

# Define the target file relative to the script location
TARGET_FILE = "sample_code/bad_code.py"
# Ensure this path is correct relative to where the script runs in GitHub Actions
TARGET_FILE_PATH = os.path.join(os.path.dirname(__file__), TARGET_FILE)
print(TARGET_FILE_PATH)

# --- MLflow Setup ---
# By default, MLflow logs to a local ./mlruns directory
mlflow.set_tracking_uri("http://localhost:8080") # Optional: if using a remote MLflow server
mlflow.set_experiment("Code Refactoring PoC")

# --- Main Execution Logic ---
if __name__ == "__main__":
    if not os.path.exists(TARGET_FILE_PATH):
        logging.error(f"Target file not found: {TARGET_FILE_PATH}")
        exit(1)
        
    # Check for API Key before starting
    if not os.environ.get("OPENAI_API_KEY"):
        logging.error("FATAL: OPENAI_API_KEY environment variable not set.")
        exit(1)
    # Check for GitHub Token (needed implicitly by gh cli)
    if not os.environ.get("GITHUB_TOKEN"):
        logging.warning("GITHUB_TOKEN environment variable not set. PR creation might fail.")
        # Don't exit, gh might have auth via other means in GHA, but good to warn.

    with mlflow.start_run() as run:
        run_id = run.info.run_id
        logging.info(f"Starting MLflow Run: {run_id}")
        mlflow.log_param("target_file", TARGET_FILE)
        refactor_goal = "Make code more Pythonic, readable, and add type hints."
        mlflow.log_param("refactor_goal", refactor_goal)

        try:
            # Read original code
            with open(TARGET_FILE_PATH, "r") as f:
                original_code = f.read()
            mlflow.log_text(original_code, "original_code.py")
            logging.info(f"Read original code from {TARGET_FILE_PATH}")

            # --- Agent 1: Code Improvement ---
            improver = CodeImproverAgent()
            suggested_code = improver.improve_code(original_code, refactor_goal)

            if suggested_code:
                mlflow.log_text(suggested_code, "suggested_code.py")
                logging.info("Suggestion received. Validating...")

                # --- Basic Validation ---
                validation_passed = improver.validate_code(suggested_code)
                mlflow.log_metric("validation_passed", 1 if validation_passed else 0)

                if validation_passed:
                    logging.info("Validation passed. Proceeding to create PR.")
                    # --- Agent 2: Pull Request Creation ---
                    pr_agent = PullRequestAgent()
                    # Create a unique branch name
                    branch_name = f"refactor-poc-{run_id[:8]}-{int(time.time())}"
                    pr_url = pr_agent.create_pr(TARGET_FILE_PATH, suggested_code, branch_name)

                    if pr_url:
                        logging.info(f"PR creation successful: {pr_url}")
                        mlflow.log_metric("pr_created", 1)
                        mlflow.set_tag("pull_request_url", pr_url)
                        # Log as artifact too for easy clicking in UI
                        mlflow.log_text(pr_url, "pull_request_url.txt")
                    else:
                        logging.error("PR creation failed.")
                        mlflow.log_metric("pr_created", 0)
                        mlflow.set_tag("status", "PR Creation Failed")
                else:
                    logging.warning("Validation failed. Skipping PR creation.")
                    mlflow.set_tag("status", "Validation Failed")
            else:
                logging.error("Code improvement agent failed to return suggestion.")
                mlflow.set_tag("status", "Improvement Failed")

        except Exception as e:
            logging.error(f"An error occurred in the main script: {e}", exc_info=True)
            mlflow.set_tag("status", "Error")
            mlflow.log_param("error_message", str(e))
            # Re-raise the exception so the GitHub Action fails correctly
            raise e
        finally:
            logging.info(f"MLflow Run {run_id} finished.")
            PullRequestAgent.return_to_main()
