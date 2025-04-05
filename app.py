from flask import Flask, render_template, request, jsonify, flash, session, redirect, url_for, get_flashed_messages
import joblib
import psycopg2
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import time
from Aichatbot.chat import chat
from functools import wraps
import os
import urllib.parse

# App password for sending emails
app_password = "wyhw yrii mhen nhxg"  # Replace with your actual app password
DATABASE = "database.db"


app = Flask(__name__)
app.secret_key = 'behavior'

# Loading the trained model
model = joblib.load(r"C:\Users\lokes\Downloads\Botshield-mass\Botshield-main\decision_tree_user1.pkl")

# Dictionaries to track failed attempts, lockouts, and email cooldowns
email_cooldown = {}  # Store last email time for each user
bot_detected_sessions = set()  # Store sessions that have already detected a bot
bot_lockout_times = {}  # Store the lockout times for detected bots
failed_attempts = {}  # Track failed login attempts per username
ip_failed_attempts = {}  # Track failed login attempts per IP address
lockout_duration = 300  # 5 minutes in seconds
max_failed_attempts = 5  # Maximum allowed failed attempts before lockout
email_alert_threshold = 3  # Send email alert after 3 failed attempts

def connect_to_db():
    """
    Connect to the PostgreSQL database.
    Returns:
        psycopg2.extensions.connection: Database connection object.
    Raises:
        ValueError: If DATABASE_URL is not set in production.
    """
    # Always use these credentials for local development
    try:
        return psycopg2.connect(
            dbname='mouse_patterns',
            user='postgres',
            password='loke123',
            host='localhost',
            port=5432
        )
    except Exception as e:
        print(f"Failed to connect to database: {str(e)}")
        raise

conn = connect_to_db()
cursor = conn.cursor()

def initialize_database():
    """
    Initialize the database by creating necessary tables if they don't exist.
    """
    try:
        # Create behavior_tracking table with scroll_speed column
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS behavior_tracking (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                name VARCHAR(255),
                typing_speed FLOAT,
                scroll_speed FLOAT,
                status VARCHAR(50),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Create failed_login_attempts table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS failed_login_attempts (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255),
                ip_address VARCHAR(45),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Create login table if it doesn't exist (assumed for login validation)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS login (
                user_id SERIAL PRIMARY KEY,
                name VARCHAR(255),
                email VARCHAR(255) UNIQUE,
                password VARCHAR(255)
            )
        """)
        conn.commit()
        print("Database tables initialized successfully.")
    except Exception as e:
        print(f"Error initializing database: {e}")
        conn.rollback()

# Initialize the database when the application starts
initialize_database()

# Add scroll_speed column to existing behavior_tracking table if it doesn't exist
try:
    cursor.execute("""
        ALTER TABLE behavior_tracking ADD COLUMN IF NOT EXISTS scroll_speed FLOAT;
    """)
    conn.commit()
    print("Added scroll_speed column to behavior_tracking table.")
except Exception as e:
    print(f"Error adding scroll_speed column: {e}")
    conn.rollback()

def is_account_locked(username):
    """
    Check if the account is locked due to too many failed login attempts.
    """
    if username in failed_attempts and failed_attempts[username]['locked']:
        remaining_time = lockout_duration - (time.time() - failed_attempts[username]['lock_time'])
        if remaining_time > 0:
            return True, int(remaining_time)
        else:
            # Clear lock if time has passed
            del failed_attempts[username]
    return False, 0

def is_ip_locked(ip_address):
    """
    Check if the IP address is locked due to too many failed login attempts.
    """
    if ip_address in ip_failed_attempts and ip_failed_attempts[ip_address]['locked']:
        remaining_time = lockout_duration - (time.time() - ip_failed_attempts[ip_address]['lock_time'])
        if remaining_time > 0:
            return True, int(remaining_time)
        else:
            # Clear lock if time has passed
            del ip_failed_attempts[ip_address]
    return False, 0

def log_failed_attempt(username, ip_address):
    """
    Log a failed login attempt in the database.
    """
    try:
        cursor.execute("""
            INSERT INTO failed_login_attempts (username, ip_address, timestamp)
            VALUES (%s, %s, NOW())
        """, (username, ip_address))
        conn.commit()
    except psycopg2.errors.UndefinedTable:
        # If the table doesn't exist, create it and retry
        print("Table 'failed_login_attempts' not found. Creating it now...")
        cursor.execute("""
            CREATE TABLE failed_login_attempts (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255),
                ip_address VARCHAR(45),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        # Retry the insert
        cursor.execute("""
            INSERT INTO failed_login_attempts (username, ip_address, timestamp)
            VALUES (%s, %s, NOW())
        """, (username, ip_address))
        conn.commit()
    except Exception as e:
        print(f"Error logging failed attempt: {e}")
        conn.rollback()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

def get_db_connection():
    
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL
        );
    """)


    conn.commit()
    conn.close()


def register():
    """Register a new user"""
    data = request.get_json()
    print("📩 Received Data:", data) 

    if not data:
        return jsonify({"message": "No data received"}), 400

    username = data.get("username")
    password = data.get("password")
    email = data.get("email")

    if not username or not password or not email:
        print("❌ Missing fields: Username, Password, or Email is empty")
        return jsonify({"message": "Username, password, and email are required"}), 400

    hashed_password = hash_password(password)

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("INSERT INTO users (username, password, email) VALUES (?, ?, ?)", 
                       (username, hashed_password, email))
        conn.commit()
        print("✅ Registration successful!")
        return jsonify({"message": "Registration successful"}), 201
    except sqlite3.IntegrityError as e:
        print("❌ Integrity Error:", e)
        return jsonify({"message": "Username or email already exists"}), 400
    except Exception as e:
        print("❌ Unexpected Error:", e)
        return jsonify({"message": "Internal server error"}), 500
    finally:
        conn.close()


@app.route('/')
def home():
    return render_template("about.html")

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template("dashboard.html")

@app.route('/login')
def login():
    email = session.get('last_attempted_email', '')
    ip_address = request.remote_addr
    account_locked, account_remaining_time = is_account_locked(email)
    ip_locked, ip_remaining_time = is_ip_locked(ip_address)
    
    is_locked = account_locked or ip_locked
    remaining_time = max(account_remaining_time, ip_remaining_time) if is_locked else 0
    
    if is_locked:
        flashed_messages = [msg for cat, msg in get_flashed_messages(with_categories=True)]
        lockout_message = f'Account or IP locked due to too many failed attempts. Please wait {remaining_time} seconds before trying again.'
        if lockout_message not in flashed_messages:
            flash(lockout_message, 'danger')
    
    return render_template("login.html", is_locked=is_locked, remaining_time=remaining_time)

@app.route('/login_validation', methods=['POST'])
def login_validation():
    email = request.form.get('username')
    password = request.form.get('password')
    ip_address = request.remote_addr

    session['last_attempted_email'] = email

    account_locked, account_remaining_time = is_account_locked(email)
    if account_locked:
        return redirect('/login')

    ip_locked, ip_remaining_time = is_ip_locked(ip_address)
    if ip_locked:
        return redirect('/login')

    if ip_address in bot_lockout_times:
        lockout_time = bot_lockout_times[ip_address]
        if datetime.now() < lockout_time:
            remaining_time = (lockout_time - datetime.now()).seconds
            flash(f'Access denied due to bot detection. Please wait {remaining_time} seconds before trying again.', 'danger')
            return redirect('/login')
        else:
            del bot_lockout_times[ip_address]

    cursor.execute("SELECT user_id, name, email FROM login WHERE email = %s AND password = %s", (email, password))
    user = cursor.fetchone()

    if user:
        session['user_id'] = user[0]
        session['user_name'] = user[1]
        session['user_email'] = user[2]
        session['session_count'] = 1
        
        if email in failed_attempts:
            del failed_attempts[email]
        if ip_address in ip_failed_attempts:
            del ip_failed_attempts[ip_address]
        
        return redirect('/starter')
    else:
        if email not in failed_attempts:
            failed_attempts[email] = {'count': 0, 'locked': False}
        failed_attempts[email]['count'] += 1

        if ip_address not in ip_failed_attempts:
            ip_failed_attempts[ip_address] = {'count': 0, 'locked': False}
        ip_failed_attempts[ip_address]['count'] += 1

        log_failed_attempt(email, ip_address)

        if failed_attempts[email]['count'] == email_alert_threshold:
            send_email_alert(email, "Suspicious Login Attempts", f"""
            Dear User,

            We have detected {email_alert_threshold} failed login attempts on your account from IP address {ip_address}.
            If this was not you, please secure your account immediately.

            Best regards,
            Bot Shield Team
            """)

        if failed_attempts[email]['count'] >= max_failed_attempts:
            failed_attempts[email]['locked'] = True
            failed_attempts[email]['lock_time'] = time.time()
            return redirect('/login')
        else:
            flash('Invalid email or password', 'danger')
            flash(f'Attempts left: {max_failed_attempts - failed_attempts[email]["count"]}', 'warning')

        if ip_failed_attempts[ip_address]['count'] >= max_failed_attempts:
            ip_failed_attempts[ip_address]['locked'] = True
            ip_failed_attempts[ip_address]['lock_time'] = time.time()
            return redirect('/login')

        return redirect('/login')

@app.route('/starter')
@login_required
def starter():
    name = session.get('user_name')
    if name:
        return render_template("index1.html", name=name)
    else:
        flash('Please log in first.', 'warning')
        return redirect('/login')

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard_data():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    cursor.execute("""
        SELECT name, typing_speed, scroll_speed, status, timestamp 
        FROM behavior_tracking 
        WHERE user_id = %s
        ORDER BY timestamp DESC 
        LIMIT 10
    """, (user_id,))
    recent_activities = cursor.fetchall()
    
    activities = []
    for activity in recent_activities:
        activities.append({
            "username": activity[0],
            "typing_speed": activity[1] if activity[1] is not None else 0,
            "scroll_speed": activity[2] if activity[2] is not None else 0,
            "status": activity[3],
            "timestamp": activity[4].strftime("%Y-%m-%d %H:%M:%S")
        })

    cursor.execute("""
        SELECT AVG(typing_speed)
        FROM behavior_tracking
        WHERE user_id = %s AND typing_speed IS NOT NULL AND typing_speed > 0
    """, (user_id,))
    avg_typing_speed = cursor.fetchone()[0]
    avg_typing_speed = round(float(avg_typing_speed), 1) if avg_typing_speed else 0.0

    cursor.execute("""
        SELECT AVG(scroll_speed)
        FROM behavior_tracking
        WHERE user_id = %s AND scroll_speed IS NOT NULL AND scroll_speed > 0
    """, (user_id,))
    avg_scroll_speed = cursor.fetchone()[0]
    avg_scroll_speed = round(float(avg_scroll_speed), 1) if avg_scroll_speed else 0.0

    total_sessions = session.get('session_count', 1)

    cursor.execute("SELECT COUNT(*) FROM behavior_tracking WHERE user_id = %s AND status = 'Bot'", (user_id,))
    flagged_sessions = cursor.fetchone()[0]

    return jsonify({
        "total_sessions": total_sessions,
        "flagged_sessions": flagged_sessions,
        "average_typing_speed": avg_typing_speed,
        "average_scroll_speed": avg_scroll_speed,
        "recent_activities": activities
    })

@app.route('/api/behavior', methods=['POST'])
def track_behavior():
    data = request.json
    typing_speed = data.get('typing_speed', 0)
    scroll_speed = data.get('scroll_speed', 0)
    suspicious_count = data.get('suspicious_count', 0)
    paste_count = data.get('paste_count', 0)
    user_id = session.get('user_id')
    user_name = session.get('user_name', 'Unknown')
    is_logout = data.get('is_logout', False)
    
    ip_address = request.remote_addr
    
    if user_id in bot_detected_sessions:
        return jsonify({
            "prediction": "Bot",
            "reasons": ["Bot already detected for this session"],
            "lockout": True,
            "message": "Bot behavior detected. Access denied for 54 seconds."
        })
    
    is_bot = False
    reasons = []
    status = "Human"
    
    if suspicious_count >= 3 or paste_count >= 2 or scroll_speed > 5000:
        if typing_speed > 10 or paste_count >= 2 or scroll_speed > 5000:
            is_bot = True
            if scroll_speed > 5000:
                reasons.append("Excessive scroll speed detected")
            if typing_speed > 10:
                reasons.append("Consistently abnormal typing speed detected")
            if paste_count >= 2:
                reasons.append("Multiple paste operations detected")
            status = "Bot"
    
    cursor.execute("""
        INSERT INTO behavior_tracking (user_id, name, typing_speed, scroll_speed, status, timestamp)
        VALUES (%s, %s, %s, %s, %s, NOW())
    """, (user_id, user_name, typing_speed, scroll_speed, status))
    conn.commit()
    
    if is_bot:
        bot_detected_sessions.add(user_id)
        bot_lockout_times[ip_address] = datetime.now() + timedelta(seconds=54)
        
        user_email = session.get('user_email')
        if user_email:
            current_time = datetime.now()
            last_email_time = email_cooldown.get(user_email)
            
            if not last_email_time or (current_time - last_email_time).total_seconds() > 300:
                email_cooldown[user_email] = current_time
                send_email_alert(user_email, "Bot Detected", """
                Dear User,

                An unauthorized user (bot) was detected attempting to use your account on our website. 
                As a precaution, you have been logged out automatically.

                If this was not you, please contact support immediately.

                Best regards,
                Bot Shield Team
                """)
    
    return jsonify({
        "prediction": status,
        "reasons": reasons if reasons else ["Normal behavior detected"],
        "lockout": is_bot,
        "message": "Bot behavior detected. Access denied for 54 seconds." if is_bot else "Normal behavior detected."
    })

@app.route('/api/init_db', methods=['POST'])
def init_db():
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS behavior_tracking (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                name VARCHAR(255),
                typing_speed FLOAT,
                scroll_speed FLOAT,
                status VARCHAR(50),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS failed_login_attempts (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255),
                ip_address VARCHAR(45),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        return jsonify({"message": "Database initialized successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def send_email_alert(to_email, subject, body):
    """
    Send an email alert to the user.
    """
    sender_email = "botshield6@gmail.com"
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, app_password)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()
        print(f"Alert email sent successfully to {to_email}.")
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")

@app.route("/about")
def about():
    return render_template('about.html')
@app.route("/register.html")
def register():
    return render_template('register.html')

@app.route('/logout', methods=['GET'])
def logout():
    return redirect(url_for('login'))

@app.route("/logout", methods=['POST'])
def logout_post():
    session.clear()
    return redirect('/login')

@app.route("/chat", methods=['POST'])
def chatBot():
    return chat(request)

@app.route('/account')
@login_required
def account():
    return render_template('account.html')

@app.route("/base.html")
def basepage():
    return render_template('base.html')

@app.route("/bootstrap.html")
def bootstrappage():
    return render_template('bootstrap.html')

@app.route("/dashboard.html")
def dashboardpage():
    return render_template('dashboard.html')

@app.route("/index.html")
def indexpage():
    return render_template('index.html')

@app.route("/index1.html")
def index1page():
    return render_template('index1.html')

@app.route("/successful.html")
def successfulpage():
    return render_template('successful.html')

@app.route("/temp.html")
def temppage():
    return render_template('temp.html')

@app.route("/test.html")
def testpage():
    return render_template('test.html')

if __name__ == "__main__":
    app.run(port=2000, debug=True)