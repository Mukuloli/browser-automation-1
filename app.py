#!/usr/bin/env python3
"""
Browser Automation System - Web Frontend Server.

Provides a chat-based web UI for the browser automation system.
Users interact with an AI agent that understands natural language,
asks follow-up questions, and triggers browser automation.

The workflow is interactive: when the AI needs user input (e.g.,
which flight to select), it pauses and asks via the chat.

Run this file and open http://localhost:5000 in your browser.
"""

import sys
import io
import json
import time
import base64
import threading
import queue
from datetime import datetime

from flask import Flask, render_template, request, jsonify, Response

app = Flask(__name__)

# ============================================================
# Shared State & Queues
# ============================================================

log_queue = queue.Queue()
automation_status = {"state": "idle", "message": "Ready", "started_at": None}
status_lock = threading.Lock()

# Workflow ↔ Chat interaction queues
# workflow sends questions/screenshots here → chat picks them up
workflow_to_chat = queue.Queue()
# chat sends user responses here → workflow picks them up
chat_to_workflow = queue.Queue()


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
        if self.original:
            self.original.write(text)
        return len(text) if text else 0

    def flush(self):
        if self.original:
            self.original.flush()


# ============================================================
# Chat Agent (singleton)
# ============================================================

from utils.chat_agent import ChatAgent

_chat_agent = ChatAgent()
_chat_lock = threading.Lock()


# ============================================================
# Routes
# ============================================================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Handle a user chat message.
    
    Also checks if the workflow is waiting for user input 
    (e.g., flight selection) and routes accordingly.
    """
    data = request.get_json()
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"error": "Please enter a message"}), 400

    # Check if workflow is waiting for user input
    with status_lock:
        waiting = automation_status.get("waiting_for_user", False)

    if waiting:
        # Route this message to the workflow
        chat_to_workflow.put(user_message)
        # Add to chat agent history so it stays in context
        with _chat_lock:
            _chat_agent.conversation_history.append({
                "role": "user", "text": user_message,
            })
            _chat_agent.conversation_history.append({
                "role": "assistant",
                "text": f"Got it! Selecting that option for you now... ✈️",
                "raw": json.dumps({"type": "message", "text": f"Got it! Selecting that option for you now... ✈️"}),
            })
        with status_lock:
            automation_status["waiting_for_user"] = False
        return jsonify({
            "type": "message",
            "text": "Got it! Selecting that option for you now... ✈️",
        })

    # Normal chat flow
    with _chat_lock:
        response = _chat_agent.chat(user_message)

    # If the response triggers an action, start automation
    if response.get("type") == "action":
        action = response.get("action")

        with status_lock:
            if automation_status["state"] == "running":
                response["text"] += "\n\n⚠️ An automation is already running. Please wait."
                response["type"] = "message"
                return jsonify(response)

        if action == "book_flight":
            booking_details = response.get("booking_details", {})
            thread = threading.Thread(
                target=_run_flight_booking,
                args=(booking_details,),
                daemon=True,
            )
            thread.start()

        elif action == "automate":
            goal = response.get("goal", "")
            thread = threading.Thread(
                target=_run_general_automation,
                args=(goal,),
                daemon=True,
            )
            thread.start()

    return jsonify(response)


@app.route("/api/chat/reset", methods=["POST"])
def reset_chat():
    with _chat_lock:
        _chat_agent.reset()
    # Clear interaction queues
    while not workflow_to_chat.empty():
        try: workflow_to_chat.get_nowait()
        except: pass
    while not chat_to_workflow.empty():
        try: chat_to_workflow.get_nowait()
        except: pass
    return jsonify({"status": "ok", "greeting": _chat_agent.get_greeting()})


@app.route("/api/chat/greeting")
def greeting():
    return jsonify(_chat_agent.get_greeting())


@app.route("/api/workflow-message")
def get_workflow_message():
    """
    Polled by frontend to check if workflow has a question for the user.
    Returns the question + optional screenshot base64.
    """
    try:
        msg = workflow_to_chat.get_nowait()
        return jsonify(msg)
    except queue.Empty:
        return jsonify(None)


@app.route("/api/status")
def get_status():
    with status_lock:
        return jsonify(automation_status)


@app.route("/api/logs")
def stream_logs():
    def generate():
        while True:
            try:
                log = log_queue.get(timeout=1)
                yield f"data: {json.dumps(log)}\n\n"
            except queue.Empty:
                yield f"data: {json.dumps({'heartbeat': True})}\n\n"
    return Response(generate(), mimetype="text/event-stream")


# ============================================================
# Background Workers
# ============================================================

def _set_status(state, message, **extra):
    with status_lock:
        automation_status["state"] = state
        automation_status["message"] = message
        if state == "running":
            automation_status["started_at"] = datetime.now().isoformat()
        for k, v in extra.items():
            automation_status[k] = v


def _run_general_automation(goal):
    _set_status("running", f"Running: {goal}")
    old_stdout = sys.stdout
    sys.stdout = LogCapture(old_stdout)
    try:
        from main import run
        log_queue.put({"time": datetime.now().strftime("%H:%M:%S"), "message": f"🚀 Starting: {goal}"})
        run(goal, confirm=False)
        _set_status("completed", f"Completed: {goal}")
        log_queue.put({"time": datetime.now().strftime("%H:%M:%S"), "message": "✅ Done!"})
    except Exception as e:
        _set_status("error", f"Error: {str(e)}")
        log_queue.put({"time": datetime.now().strftime("%H:%M:%S"), "message": f"❌ Error: {str(e)}"})
    finally:
        sys.stdout = old_stdout


def _run_flight_booking(booking_details):
    origin = booking_details.get("origin", "?")
    dest = booking_details.get("destination", "?")
    _set_status("running", f"Booking: {origin} → {dest}")

    old_stdout = sys.stdout
    sys.stdout = LogCapture(old_stdout)

    try:
        from utils.flight_booking_workflow import FlightBookingWorkflow
        log_queue.put({
            "time": datetime.now().strftime("%H:%M:%S"),
            "message": f"✈️ Starting: {origin} → {dest}",
        })

        workflow = FlightBookingWorkflow(
            booking_details,
            ask_user_fn=_ask_user_via_chat,
        )
        workflow.execute()

        _set_status("completed", f"Completed: {origin} → {dest}")
        log_queue.put({"time": datetime.now().strftime("%H:%M:%S"), "message": "✅ Flight booking done!"})
    except Exception as e:
        _set_status("error", f"Error: {str(e)}")
        log_queue.put({"time": datetime.now().strftime("%H:%M:%S"), "message": f"❌ Error: {str(e)}"})
    finally:
        sys.stdout = old_stdout


def _ask_user_via_chat(question: str, screenshot_b64: str = None) -> str:
    """
    Called by the workflow when it needs user input.
    
    Sends the question (+ optional screenshot) to the chat UI,
    then blocks until the user responds.
    """
    # Signal that we're waiting
    _set_status("running", "Waiting for your choice...", waiting_for_user=True)

    # Send question to frontend
    msg = {"type": "workflow_question", "text": question}
    if screenshot_b64:
        msg["screenshot"] = screenshot_b64
    workflow_to_chat.put(msg)

    # Block until user responds via chat
    user_response = chat_to_workflow.get(timeout=300)  # 5 min timeout
    
    _set_status("running", "Continuing automation...")
    return user_response


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🤖 Browser Automation System — Chat UI")
    print("=" * 60)
    print("\n🌐 Open http://localhost:5000 in your browser\n")
    app.run(debug=False, host="0.0.0.0", port=5000)
