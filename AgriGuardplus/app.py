from flask import Flask, render_template, jsonify, request, url_for, Response, session, redirect
import cv2 
import mysql.connector
from mysql.connector import pooling 
from werkzeug.security import generate_password_hash, check_password_hash
from ultralytics import YOLO
import os
from datetime import datetime
import threading
import time
from playsound import playsound 
import numpy as np 
import requests 
import re 
import smtplib 
import random 
from email.mime.text import MIMEText 
from email.mime.multipart import MIMEMultipart 

from flask_talisman import Talisman 
from flask_caching import Cache     
from dotenv import load_dotenv      

load_dotenv()

app = Flask(__name__)

# --- CONFIGURATION ---
app.secret_key = os.getenv('SECRET_KEY', 'AgriGuard_Secure_Key_2025')
Talisman(app, content_security_policy=None, force_https=False) 
app.config['CACHE_TYPE'] = 'SimpleCache' 
app.config['CACHE_DEFAULT_TIMEOUT'] = 300
cache = Cache(app)

DETECTIONS_FOLDER = os.path.join('static', 'detections')
os.makedirs(DETECTIONS_FOLDER, exist_ok=True) 

# --- YOUR EMAIL CREDENTIALS ---
SMTP_EMAIL = "omkarjntucollege@gmail.com" 
SMTP_PASSWORD = "ayzw wdln onbd zatn"      

# --- GLOBAL VARS ---
system_status = {'status': 'OFF'} 
current_frame = None 
lock = threading.Lock() 
last_detection_time = None
model = None 
otp_storage = {} 

# --- MYSQL CONFIGURATION ---
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '1234', 
    'database': 'agriguard_db'
}

connection_pool = None
try:
    connection_pool = pooling.MySQLConnectionPool(pool_name="agri_pool", pool_size=5, pool_reset_session=True, **db_config)
    print("✅ Database Pool Created.")
except Exception as e: print(f"❌ DB Error: {e}")

# --- HELPER: SEND EMAIL ---
def send_email(to_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.send_message(msg); server.quit()
        return True
    except Exception as e: return False

# ==========================================
#    ALERT LOGIC (FILTERED)
# ==========================================
def trigger_remote_alert(phone_ip, animal_name):
    # Since we are using laptop camera, phone flash logic won't work unless you have a separate IP
    # But we keep the function structure to avoid errors.
    base_url = f"http://{phone_ip}"
    
    # 1. Blink Light (Skipped if IP is 0.0.0.0)
    def blink_light():
        try:
            for _ in range(3): 
                requests.get(f"{base_url}/enabletorch", timeout=1) 
                time.sleep(0.3)
                requests.get(f"{base_url}/disabletorch", timeout=1) 
                time.sleep(0.3)
        except Exception as e: print(f"Phone Flash Error: {e}")
    
    if "0.0.0.0" not in phone_ip:
        threading.Thread(target=blink_light).start()
    
    # 2. Sound Logic (Double Check: Animals Only)
    try:
        ignore_list = ['person', 'man', 'woman', 'car', 'truck', 'bus', 'bike']
        name = animal_name.lower()
        
        if not any(x in name for x in ignore_list):
            sound_file = 'static/sounds/beast.wav' if 'elephant' in name else 'static/sounds/lion.wav'
            if os.path.exists(sound_file): 
                playsound(sound_file)
                print(f"🔊 Playing Sound for: {animal_name}")
            else:
                print("❌ Sound file missing.")
        else:
            print(f"🔇 Silent Detection: {animal_name}")
            
    except Exception as e: print(f"Laptop Audio Error: {e}")

# --- HELPER: DATABASE INIT ---
def init_db():
    if connection_pool is None: return
    try:
        conn = connection_pool.get_connection()
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (id INT AUTO_INCREMENT PRIMARY KEY, first_name VARCHAR(255) NOT NULL, last_name VARCHAR(255) NOT NULL, email VARCHAR(255) NOT NULL UNIQUE, password_hash VARCHAR(255) NOT NULL)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS detections (id INT AUTO_INCREMENT PRIMARY KEY, timestamp DATETIME NOT NULL, animal_name VARCHAR(255) NOT NULL, image_path VARCHAR(255) NOT NULL)''')
        conn.commit(); cursor.close(); conn.close()
    except Exception as e: print(f"DB Init Error: {e}")

# ==========================================
#        SURVEILLANCE LOOP (OS CAMERA)
# ==========================================
def surveillance_loop():
    global current_frame, system_status, last_detection_time, model
    
    # Placeholder IP (Flash won't trigger on laptop)
    PHONE_IP = "0.0.0.0" 

    # --- TARGET ANIMALS LIST ---
    TARGET_ANIMALS = ['bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra', 'giraffe', 'monkey', 'boar']

    if model is None:
        try:
            print("Loading AI Model..."); model = YOLO('yolo11n.pt'); print("✅ AI Model Loaded.")
        except Exception as e: print(f"❌ Model Error: {e}"); model = None
    
    # --- CHANGED: Use Index 0 for Laptop/OS Camera ---
    camera = cv2.VideoCapture(0)
    print("--- Surveillance Started: Laptop Camera (Index 0) ---")
    
    while True:
        if system_status['status'] == 'OFF':
            if camera.isOpened(): camera.release()
            blank = np.zeros((480, 640, 3), np.uint8); cv2.putText(blank, "SYSTEM OFFLINE", (180, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
            with lock: current_frame = blank.copy()
            time.sleep(1); continue

        if not camera.isOpened(): 
            camera = cv2.VideoCapture(0)
            time.sleep(2); continue

        success, frame = camera.read()
        if not success: 
            time.sleep(0.5); continue

        annotated_frame = frame.copy()

        if model:
            results = model(frame, verbose=False)
            for r in results:
                # 1. DRAW BOXES (For everything)
                annotated_frame = r.plot()
                
                # 2. FILTER: Check if any TARGET ANIMAL is present
                detected_target = None
                for c in r.boxes.cls:
                    class_name = model.names[int(c)]
                    if class_name in TARGET_ANIMALS:
                        detected_target = class_name
                        break 
                
                # 3. ACTION: Save & Alert ONLY if target found
                if detected_target:
                    current_time = datetime.now()
                    if last_detection_time is None or (current_time - last_detection_time).total_seconds() > 10:
                        last_detection_time = current_time
                        
                        print(f"!!! TARGET DETECTED: {detected_target} !!!")
                        
                        # Save Image
                        filename = f"detection_{current_time.strftime('%Y%m%d_%H%M%S')}.jpg"
                        full_path = os.path.join(DETECTIONS_FOLDER, filename)
                        web_path = f"static/detections/{filename}"
                        cv2.imwrite(full_path, annotated_frame)
                        
                        # Save to Database
                        if connection_pool:
                            try:
                                conn = connection_pool.get_connection(); cursor = conn.cursor()
                                cursor.execute("INSERT INTO detections (timestamp, animal_name, image_path) VALUES (%s, %s, %s)", (current_time, detected_target, web_path))
                                conn.commit(); cursor.close(); conn.close()
                            except Exception as e: print(f"DB Save Error: {e}")
                        
                        # Trigger Alert
                        threading.Thread(target=trigger_remote_alert, args=(PHONE_IP, detected_target)).start()
        
        with lock: current_frame = annotated_frame.copy()
        time.sleep(0.01)

# ==========================================
#              FLASK ROUTES
# ==========================================

@app.route('/')
def home():
    is_logged_in = 'user_id' in session
    return render_template('home.html', logged_in=is_logged_in)

@app.route('/auth')
def index():
    session.clear() 
    return render_template('index.html')

@app.route('/data')
def data():
    if 'user_id' not in session: return redirect(url_for('index'))
    return render_template('data.html')

@app.route('/live')
def live():
    if 'user_id' not in session: return redirect(url_for('index'))
    return render_template('live.html')

@app.route('/api/status', methods=['GET'])
def get_status(): return jsonify(system_status)

@app.route('/api/status/toggle', methods=['POST'])
def toggle_status():
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 401
    global system_status
    data = request.json
    if 'status' in data:
        system_status['status'] = data['status']
        return jsonify({'success': True, 'new_status': system_status['status']})
    return jsonify({'success': False}), 400

@app.route('/api/detections', methods=['GET'])
@cache.cached(timeout=5, key_prefix='all_detections') 
def get_detections():
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 401
    if not connection_pool: return jsonify([]), 500
    try:
        conn = connection_pool.get_connection(); cursor = conn.cursor()
        cursor.execute("SELECT id, timestamp, animal_name, image_path FROM detections ORDER BY timestamp DESC")
        rows = cursor.fetchall(); cursor.close(); conn.close()
        result = [{"id": r[0], "timestamp": r[1].strftime('%Y-%m-%d %H:%M:%S'), "animal_name": r[2], "image_path": r[3]} for r in rows]
        return jsonify(result)
    except: return jsonify([]), 500

@app.route('/api/detections/delete', methods=['POST'])
def delete_detections():
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 401
    data = request.json; ids = data.get('ids', []); paths = data.get('image_paths', [])
    if not ids: return jsonify({'success': False}), 400
    try:
        conn = connection_pool.get_connection(); cursor = conn.cursor()
        placeholders = ','.join(['%s'] * len(ids))
        cursor.execute(f"DELETE FROM detections WHERE id IN ({placeholders})", tuple(ids))
        conn.commit(); cursor.close(); conn.close()
        cache.delete('all_detections')
        for p in paths:
            try:
                filename = os.path.basename(p)
                sys_path = os.path.join(DETECTIONS_FOLDER, filename)
                if os.path.exists(sys_path): os.remove(sys_path)
            except: pass
        return jsonify({'success': True})
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.json
        if not data: return jsonify({'success': False, 'message': 'No data'}), 400
        email = data.get('email', '').strip().lower(); password = data.get('password', '')
        if '@' not in email: return jsonify({'success': False, 'message': 'Invalid Email'}), 400
        conn = connection_pool.get_connection(); cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone(): cursor.close(); conn.close(); return jsonify({'success': False, 'message': 'Email Exists'})
        cursor.execute("INSERT INTO users (first_name, last_name, email, password_hash) VALUES (%s, %s, %s, %s)",
            (data['first_name'], data['last_name'], email, generate_password_hash(password)))
        conn.commit(); cursor.close(); conn.close()
        return jsonify({'success': True, 'message': 'Registered!'})
    except Exception as e: return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    if not connection_pool: return jsonify({'success': False, 'message': 'DB Error'}), 500
    try:
        conn = connection_pool.get_connection(); cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (data['email'],))
        user = cursor.fetchone(); cursor.close(); conn.close()
        if user and check_password_hash(user[4], data['password']):
            otp = str(random.randint(100000, 999999))
            otp_storage[data['email']] = {'otp': otp, 'type': 'login', 'timestamp': time.time()}
            if send_email(data['email'], "AgriGuard Login Code", f"OTP: {otp}"):
                return jsonify({'success': True, 'require_otp': True, 'message': 'OTP Sent'})
            return jsonify({'success': False, 'message': 'Email Failed'})
        return jsonify({'success': False, 'message': 'Invalid Credentials'}), 401
    except Exception as e: return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/verify_login', methods=['POST'])
def verify_login():
    data = request.json; email = data.get('email'); otp = data.get('otp')
    if email in otp_storage:
        stored = otp_storage[email]
        if stored['type'] == 'login' and stored['otp'] == otp:
            conn = connection_pool.get_connection(); cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            user = cursor.fetchone(); cursor.close(); conn.close()
            session['user_id'] = user[0]
            del otp_storage[email]
            return jsonify({'success': True, 'redirect_url': url_for('home')})
    return jsonify({'success': False, 'message': 'Invalid OTP'})

@app.route('/request_reset', methods=['POST'])
def request_reset():
    email = request.json.get('email')
    conn = connection_pool.get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
    user = cursor.fetchone(); cursor.close(); conn.close()
    if not user: return jsonify({'success': False, 'message': 'Email not found'})
    otp = str(random.randint(100000, 999999))
    otp_storage[email] = {'otp': otp, 'type': 'reset', 'timestamp': time.time()}
    if send_email(email, "Reset Password OTP", f"Your OTP to reset password is: {otp}"):
        return jsonify({'success': True, 'message': 'OTP Sent'})
    return jsonify({'success': False, 'message': 'Email Failed'})

@app.route('/reset_password', methods=['POST'])
def reset_password():
    data = request.json; email = data.get('email'); otp = data.get('otp'); new_pass = data.get('new_password')
    if email in otp_storage:
        stored = otp_storage[email]
        if stored['type'] == 'reset' and stored['otp'] == otp:
            conn = connection_pool.get_connection(); cursor = conn.cursor()
            cursor.execute("UPDATE users SET password_hash = %s WHERE email = %s", (generate_password_hash(new_pass), email))
            conn.commit(); cursor.close(); conn.close()
            del otp_storage[email]
            send_email(email, "Password Changed", "Your password has been successfully updated.")
            return jsonify({'success': True, 'message': 'Password Updated! Please Login.'})
    return jsonify({'success': False, 'message': 'Invalid OTP'})

def generate_frames():
    global current_frame
    while True:
        with lock:
            if current_frame is None: 
                time.sleep(0.1)
                continue
            frame_to_encode = current_frame.copy()
        
        ret, buffer = cv2.imencode('.jpg', frame_to_encode)
        if not ret: continue
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.04) 

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    init_db()
    t = threading.Thread(target=surveillance_loop)
    t.daemon = True 
    t.start()
    app.run(debug=True, host='0.0.0.0', port=5000)