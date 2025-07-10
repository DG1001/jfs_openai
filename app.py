import os
import threading
import time
import json
import imghdr
import base64
from datetime import datetime

from flask import Flask, request, jsonify, render_template, send_from_directory

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
DATA_FILE = os.path.join(BASE_DIR, 'data.json')
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB
IMAGE_LIFETIME = 15  # seconds (5s visible + 10s fade-out)

# 1x1 transparent PNG for icon-192.png
ICON_BASE64 = (
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAA'
)
STATIC_ICON_PATH = os.path.join(BASE_DIR, 'static', 'icon-192.png')

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Thread lock for data file
lock = threading.Lock()

def init_app():
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, 'static'), exist_ok=True)
    # Generate icon file if missing
    if not os.path.exists(STATIC_ICON_PATH):
        with open(STATIC_ICON_PATH, 'wb') as f:
            f.write(base64.b64decode(ICON_BASE64))
    # Initialize data file
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w') as f:
            json.dump([], f)

def load_data():
    with lock:
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return []

def save_data(data):
    with lock:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f)

def cleanup_task():
    while True:
        now = datetime.now()
        data = load_data()
        updated = False
        for item in data[:]:
            ts = datetime.fromisoformat(item['timestamp'])
            if (now - ts).total_seconds() >= IMAGE_LIFETIME:
                # remove file
                path = os.path.join(UPLOAD_FOLDER, item['filename'])
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception:
                        pass
                data.remove(item)
                updated = True
        if updated:
            save_data(data)
        time.sleep(1)

def allowed_file(filename):
    ext = filename.rsplit('.', 1)[-1].lower()
    return ext in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/gallery')
def gallery():
    return render_template('gallery.html')

@app.route('/api/images')
def api_images():
    data = load_data()
    return jsonify(data)

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/upload', methods=['POST'])
def upload():
    if 'image' not in request.files:
        return jsonify({'success': False, 'error': 'Keine Datei im Request'}), 400
    file = request.files['image']
    comment = request.form.get('comment', '').strip()
    if not file or file.filename == '':
        return jsonify({'success': False, 'error': 'Keine Datei ausgewählt'}), 400
    if len(comment) > 100:
        return jsonify({'success': False, 'error': 'Kommentar zu lang'}), 400
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'error': 'Ungültiger Dateityp'}), 400
    # Validate image header
    file.stream.seek(0)
    header = file.stream.read(512)
    file.stream.seek(0)
    kind = imghdr.what(None, header)
    ext = file.filename.rsplit('.', 1)[-1].lower()
    if kind not in ('jpeg', 'png') and ext != 'webp':
        return jsonify({'success': False, 'error': 'Ungültige Bilddatei'}), 400
    timestamp = datetime.now().isoformat()
    filename = f"{timestamp}.{ext}"
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(save_path)
    data = load_data()
    data.append({'filename': filename, 'comment': comment, 'timestamp': timestamp})
    # Enforce capacity
    while len(data) > 10:
        old = data.pop(0)
        old_path = os.path.join(app.config['UPLOAD_FOLDER'], old['filename'])
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except Exception:
                pass
    save_data(data)
    return jsonify({'success': True})

if __name__ == '__main__':
    init_app()
    cleaner = threading.Thread(target=cleanup_task, daemon=True)
    cleaner.start()
    app.run(host='0.0.0.0', port=5000)
