"""Open the tool's Chrome window so you can sign in to Google Flow, without an AI client.

Run:  .venv/bin/python examples/sign_in.py
It waits up to 10 minutes for you to finish signing in, then saves the sign-in.
"""

from flow_mcp.browser_engine import login_and_verify_flow_session

if __name__ == "__main__":
    result = login_and_verify_flow_session(wait_seconds=600)
    print("STATUS:", result["status"])
