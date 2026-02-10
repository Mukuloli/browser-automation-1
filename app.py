#!/usr/bin/env python3
"""
Browser Automation System - Web Frontend Server.

Provides a full-screen web UI for the browser automation system.
Run this file and open http://localhost:5000 in your browser.

Usage:
    python app.py
"""

import sys
import io
import json
import time
import threading
import queue
from datetime import datetime

from flask import Flask, render_template, request, jsonify, Response

app = Flask(__name__)

# ============================================================
# Log Capture System
# ============================================================

log_queue = queue.Queue()
automation_status = {"state": "idle", "message": "Ready", "started_at": None}
status_lock = threading.Lock()


class LogCapture(io.TextIOBase):
    """Captures print output and sends it to the log queue."""

    def __init__(self, original_stdout):
        self.original = original_stdout

    def write(self, text):
        if text and text.strip():
            log_queue.put({
                "time": datetime.now().strftime("%H:%M:%S"),
                "message": text.strip(),
            })
        # Also print to original stdout for debugging
        if self.original:
            self.original.write(text)
        return len(text) if text else 0

    def flush(self):
        if self.original:
            self.original.flush()


# ============================================================
# Routes
# ============================================================

@app.route("/")
def index():
    """Serve the main UI."""
    return render_template("index.html")


@app.route("/api/status")
def get_status():
    """Return current automation status."""
    with status_lock:
        return jsonify(automation_status)


@app.route("/api/run", methods=["POST"])
def run_automation():
    """Start a general browser automation task."""
    data = request.get_json()
    goal = data.get("goal", "").strip()

    if not goal:
        return jsonify({"error": "Please enter a task"}), 400

    with status_lock:
        if automation_status["state"] == "running":
            return jsonify({"error": "Automation is already running"}), 409

    # Start automation in background thread
    thread = threading.Thread(target=_run_general_automation, args=(goal,), daemon=True)
    thread.start()

    return jsonify({"status": "started", "goal": goal})


@app.route("/api/flight-booking", methods=["POST"])
def run_flight_booking():
    """Start a flight booking automation task."""
    data = request.get_json()

    # Validate required fields
    required = ["origin", "destination", "departure_date", "trip_type"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"Missing required field: {field}"}), 400

    with status_lock:
        if automation_status["state"] == "running":
            return jsonify({"error": "Automation is already running"}), 409

    # Build booking details dict matching what the system expects
    booking_details = {
        "origin": data["origin"],
        "destination": data["destination"],
        "departure_date": data["departure_date"],
        "trip_type": data["trip_type"],
        "return_date": data.get("return_date", ""),
        "time_preference": data.get("time_preference", "any"),
        "passengers": {
            "adults": int(data.get("adults", 1)),
            "children": int(data.get("children", 0)),
            "infants": int(data.get("infants", 0)),
        },
        "class": data.get("travel_class", "economy"),
        "flexible_dates": int(data.get("flexible_dates", 0)),
    }

    thread = threading.Thread(
        target=_run_flight_booking, args=(booking_details,), daemon=True
    )
    thread.start()

    return jsonify({"status": "started", "booking": booking_details})


@app.route("/api/logs")
def stream_logs():
    """SSE endpoint — streams real-time logs to the frontend."""

    def generate():
        while True:
            try:
                log = log_queue.get(timeout=1)
                yield f"data: {json.dumps(log)}\n\n"
            except queue.Empty:
                # Send heartbeat to keep connection alive
                yield f"data: {json.dumps({'heartbeat': True})}\n\n"

    return Response(generate(), mimetype="text/event-stream")


# ============================================================
# Background Workers
# ============================================================

def _set_status(state, message):
    with status_lock:
        automation_status["state"] = state
        automation_status["message"] = message
        if state == "running":
            automation_status["started_at"] = datetime.now().isoformat()


def _run_general_automation(goal):
    """Run general browser automation in background."""
    _set_status("running", f"Running: {goal}")

    # Redirect stdout to capture logs
    old_stdout = sys.stdout
    sys.stdout = LogCapture(old_stdout)

    try:
        from main import run
        log_queue.put({"time": datetime.now().strftime("%H:%M:%S"), "message": f"🚀 Starting: {goal}"})
        run(goal, confirm=False)
        _set_status("completed", f"Completed: {goal}")
        log_queue.put({"time": datetime.now().strftime("%H:%M:%S"), "message": "✅ Automation completed!"})
    except Exception as e:
        _set_status("error", f"Error: {str(e)}")
        log_queue.put({"time": datetime.now().strftime("%H:%M:%S"), "message": f"❌ Error: {str(e)}"})
    finally:
        sys.stdout = old_stdout


def _run_flight_booking(booking_details):
    """Run flight booking automation in background."""
    origin = booking_details["origin"]
    dest = booking_details["destination"]
    _set_status("running", f"Booking: {origin} → {dest}")

    old_stdout = sys.stdout
    sys.stdout = LogCapture(old_stdout)

    try:
        from utils.flight_booking_workflow import execute_flight_booking
        log_queue.put({
            "time": datetime.now().strftime("%H:%M:%S"),
            "message": f"✈️ Starting flight booking: {origin} → {dest}",
        })
        execute_flight_booking(booking_details)
        _set_status("completed", f"Completed: {origin} → {dest}")
        log_queue.put({"time": datetime.now().strftime("%H:%M:%S"), "message": "✅ Flight booking completed!"})
    except Exception as e:
        _set_status("error", f"Error: {str(e)}")
        log_queue.put({"time": datetime.now().strftime("%H:%M:%S"), "message": f"❌ Error: {str(e)}"})
    finally:
        sys.stdout = old_stdout


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🤖 Browser Automation System — Web UI")
    print("=" * 60)
    print("\n🌐 Open http://localhost:5000 in your browser\n")
    app.run(debug=False, host="0.0.0.0", port=5000)
