"""Deploy to PythonAnywhere via its web API (no SSH required on free-tier accounts).

Creates a console, runs git pull + pip install + migrate + collectstatic through it,
then reloads the web app. Requires these environment variables:

    PA_API_TOKEN     PythonAnywhere API token (Account -> API Token)
    PA_USERNAME      PythonAnywhere username
    PA_DOMAIN        Web app domain, e.g. "yourusername.pythonanywhere.com"
    PA_PROJECT_PATH  Absolute path to the project on PythonAnywhere, e.g.
                      "/home/yourusername/RentApp"
    PA_VENV_PATH     Absolute path to the virtualenv, e.g.
                      "/home/yourusername/.virtualenvs/rentapp"
"""

import os
import sys
import time

import requests

API_BASE = "https://www.pythonanywhere.com/api/v0/user/{username}/"
POLL_INTERVAL_SECONDS = 3
TIMEOUT_SECONDS = 300
DONE_MARKER = "__DEPLOY_OK__"
FAIL_MARKER = "__DEPLOY_FAILED__"


def _env(name):
    value = os.environ.get(name)
    if not value:
        print(f"Missing required environment variable: {name}", file=sys.stderr)
        sys.exit(1)
    return value


def main():
    api_token = _env("PA_API_TOKEN")
    username = _env("PA_USERNAME")
    domain = _env("PA_DOMAIN")
    project_path = _env("PA_PROJECT_PATH")
    venv_path = _env("PA_VENV_PATH")

    base_url = API_BASE.format(username=username)
    headers = {"Authorization": f"Token {api_token}"}

    print("Creating console...")
    response = requests.post(
        f"{base_url}consoles/",
        headers=headers,
        json={"executable": "bash", "working_directory": project_path},
        timeout=30,
    )
    response.raise_for_status()
    console_id = response.json()["id"]
    print(f"Console {console_id} created.")

    try:
        deploy_command = (
            f"cd {project_path} && "
            f"source {venv_path}/bin/activate && "
            "git pull origin main && "
            "pip install -r requirements.txt && "
            "python manage.py migrate --noinput && "
            "python manage.py collectstatic --noinput && "
            f"echo {DONE_MARKER} || echo {FAIL_MARKER}"
        )
        print("Sending deploy command...")
        requests.post(
            f"{base_url}consoles/{console_id}/send_input/",
            headers=headers,
            json={"input": deploy_command + "\n"},
            timeout=30,
        ).raise_for_status()

        print("Waiting for deploy to finish...")
        elapsed = 0
        output = ""
        while elapsed < TIMEOUT_SECONDS:
            time.sleep(POLL_INTERVAL_SECONDS)
            elapsed += POLL_INTERVAL_SECONDS
            out_response = requests.get(
                f"{base_url}consoles/{console_id}/get_latest_output/",
                headers=headers,
                timeout=30,
            )
            out_response.raise_for_status()
            output = out_response.json().get("output", "")
            if DONE_MARKER in output:
                print(output)
                print("Deploy commands completed successfully.")
                break
            if FAIL_MARKER in output:
                print(output)
                print("Deploy commands failed.", file=sys.stderr)
                sys.exit(1)
        else:
            print(output)
            print(f"Timed out after {TIMEOUT_SECONDS}s waiting for deploy to finish.", file=sys.stderr)
            sys.exit(1)
    finally:
        requests.delete(f"{base_url}consoles/{console_id}/", headers=headers, timeout=30)
        print(f"Console {console_id} closed.")

    print("Reloading web app...")
    reload_response = requests.post(
        f"{base_url}webapps/{domain}/reload/", headers=headers, timeout=60
    )
    reload_response.raise_for_status()
    print("Web app reloaded. Deploy complete.")


if __name__ == "__main__":
    main()
