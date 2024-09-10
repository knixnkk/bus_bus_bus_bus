import threading
import time
from flask import Flask, render_template, request, redirect, flash, url_for, session, jsonify, session, Response
import os
import socket
from werkzeug.utils import secure_filename
import json
from serial import Serial
from pynmeagps import NMEAReader
import logging
app = Flask(__name__)

# Your existing Flask app setup

def countdown_task(duration):
    """Background task to handle countdown."""
    time.sleep(duration)
    print('Times up')
@app.route('/timer', methods=["POST"])
def timer():
    try:
        data = request.get_data()
        duration = int(data.decode('utf-8'))  # Assuming the data is sent as plain text

        # Start countdown in a new thread
        threading.Thread(target=countdown_task, args=[duration]).start()

        return jsonify({'status': 'Countdown started', 'duration': duration}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    app.secret_key="anystringhere"
    app.config['SESSION_TYPE'] = 'filesystem'
    app.run(host=socket.gethostbyname(socket.gethostname()),debug=True)
