import os
import threading
import traceback
import logging
from datetime import datetime
from flask import Flask, jsonify, request
from agent import run_daily_post

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

run_state = {
    "status": "idle",
    "last_run": None,
    "last_result": None,
    "last_error": None,
}

def run_in_background(day_num=None):
    run_state["status"] = "running"
    run_state["last_run"] = datetime.utcnow().isoformat()
    try:
        result = run_daily_post(day_num)
        run_state["status"] = "success"
        run_state["last_result"] = result
        run_state["last_error"] = None
    except Exception:
        run_state["status"] = "error"
        run_state["last_error"] = traceback.format_exc()
        logger.error(run_state["last_error"])

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "agent": "li-post-agent", "run_state": run_state})

@app.route("/status", methods=["GET"])
def status():
    return jsonify(run_state)

@app.route("/run", methods=["POST"])
def run():
    if run_state["status"] == "running":
        return jsonify({"status": "already_running"}), 409
    body = request.get_json(silent=True) or {}
    day_num = body.get("day_num")
    t = threading.Thread(target=run_in_background, args=(day_num,))
    t.daemon = True
    t.start()
    return jsonify({"status": "started", "message": "Post generation started. Check /status."})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
