import subprocess
import sys

from flask import Flask, Response

app = Flask(__name__)

@app.route("/")
def test_joblib():
    output = []

    # Python version
    output.append(f"Python version: {sys.version}")

    # Try importing joblib
    try:
        import joblib
        output.append("joblib is installed!")
    except ModuleNotFoundError:
        output.append("joblib is NOT installed!")

    # List installed packages
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True
        )
        output.append(result.stdout)
    except Exception as e:
        output.append(f"Error listing packages: {e}")

    return Response("<br>".join(output), mimetype="text/html")
