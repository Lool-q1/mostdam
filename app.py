from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'mostdam_2026'

# إعدادات أمان إضافية للجلسة (Sessions)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# --- 1. إعداد قاعدة البيانات بشكل ديناميكي ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'platform.db')

def get_db_connection():
    """فتح الاتصال مع تفعيل Row factory ليقرأ الـ HTML الحقول بأسمائها مباشرة"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # جدول المستخدمين
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        phone TEXT,
        city TEXT,
        password TEXT NOT NULL
    )''')

    # جدول المنتجات
    cursor.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        price REAL NOT NULL,
        stock INTEGER DEFAULT 0
    )''')

    # جدول الطلبات
    cursor.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        product_name TEXT,
        amount REAL,
        order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'قيد المراجعة',
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')

    # جدول الفعاليات
    cursor.execute('''CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        date_time TEXT,
        location TEXT
    )''')

    # جدول تسجيل الفعاليات
    cursor.execute('''CREATE TABLE IF NOT EXISTS event_registrations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        event_id INTEGER,
        reg_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (event_id) REFERENCES events (id)
    )''')

    # جدول النشرة البريدية
    cursor.execute('''CREATE TABLE IF NOT EXISTS newsletter (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        subscription_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    conn.close()

def seed_data():
    """تحديث جدول الفعاليات بالتفاصيل الحقيقية ليقرأها الموقع تلقائياً"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # الفعالية رقم 1 (ورشة الاستدامة المالية)
    cursor.execute('''INSERT INTO events (id, title, description, date_time, location) 
                      VALUES (1, 'الاستدامة المالية وبناء مستقبل اقتصادي', 'محاور ورشة الاستدامة المالية', '2026-05-13 19:00', 'عبر مساحة (X)')
                      ON CONFLICT(id) DO UPDATE SET 
                      title=excluded.title, description=excluded.description, date_time=excluded.date_time, location=excluded.location''')
        
    # الفعالية رقم 2 (الحفل الختامي) - تم تحديث الموعد الحقيقي والموقع الفعلي
    cursor.execute('''INSERT INTO events (id, title, description, date_time, location) 
                      VALUES (2, 'الأمسية الاستثنائية والحفل الختامي لمبادرة مستدام', 'فعاليات الحفل الختامي وتكريم المشاركين', '2026-05-18 16:00', 'غرفة أبها التجارية')
                      ON CONFLICT(id) DO UPDATE SET 
                      title=excluded.title, description=excluded.description, date_time=excluded.date_time, location=excluded.location''')
        
    conn.commit()
    conn.close()

init_db()
seed_data()

# --- 2. مسارات النظام (Routes) ---

@app.route('/')
def index():
    user_name = session.get('user_name')
    return render_template('index.html', user_name=user_name)

@app.route('/subscribe', methods=['POST'])
def subscribe():
    email = request.form.get('subscriber_email', '').strip()
    if email:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO newsletter (email) VALUES (?)", (email,))
            conn.commit()
            msg = "تم الاشتراك بنجاح في النشرة البريدية!"
        except sqlite3.IntegrityError:
            msg = "هذا البريد مسجل مسبقاً لدينا."
        except Exception:
            msg = "حدث خطأ ما، يرجى المحاولة لاحقاً."
        finally:
            conn.close()
        return f"<script>alert('{msg}'); window.location.href='/';</script>"
    return redirect(url_for('index'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        city = request.form.get('city', '').strip()   
        phone = request.form.get('phone', '').strip() 
        password = request.form.get('password', '')

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (full_name, email, phone, city, password) VALUES (?, ?, ?, ?, ?)", 
               (name, email, phone, city, password))
            user_id = cursor.lastrowid
            conn.commit()
            conn.close()
            session['user_id'] = user_id
            session['user_name'] = name
            return redirect(url_for('index'))
        except sqlite3.IntegrityError:
            if conn: conn.close()
            return redirect(url_for('signup', status='exists'))
        except Exception:
            if conn: conn.close()
            return redirect(url_for('signup', status='error'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').lower().strip()
        password = request.form.get('password', '')
        conn = get_db_connection()
        cursor = conn.cursor()
        user = cursor.execute("SELECT * FROM users WHERE email=? AND password=?", 
                              (email, password)).fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']
            session['user_name'] = user['full_name']
            return redirect(url_for('index'))
        else:
            return redirect(url_for('login', error='wrong_creds'))
    return render_template('login.html')

@app.route('/store')
def store():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products")
    all_products = cursor.fetchall()
    conn.close()
    return render_template('store.html', products=all_products)

@app.route('/checkout', methods=['POST'])
def checkout():
    if 'user_id' not in session: return redirect(url_for('login'))
    cart_data = request.form.get('cart_data')
    if not cart_data: return redirect(url_for('store'))
    
    items = json.loads(cart_data)
    conn = get_db_connection()
    cursor = conn.cursor()
    for item in items:
        cursor.execute("INSERT INTO orders (user_id, product_name, amount) VALUES (?, ?, ?)",
                       (session['user_id'], item['name'], item['price']))
    conn.commit()
    conn.close()
    return "<script>alert('تم الشراء بنجاح'); window.location.href='/profile';</script>"

@app.route('/programs')
def programs():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events")
    all_events = cursor.fetchall()
    conn.close()
    return render_template('programs.html', events=all_events)

@app.route('/register_event', methods=['POST'])
def register_event():
    if 'user_id' not in session:
        return "Unauthorized", 401
    
    event_id = request.form.get('event_id')
    user_id = session['user_id']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    event_exists = cursor.execute("SELECT id FROM events WHERE id=?", (event_id,)).fetchone()
    existing_reg = cursor.execute("SELECT id FROM event_registrations WHERE user_id=? AND event_id=?", 
                                  (user_id, event_id)).fetchone()

    if event_exists and not existing_reg:
        cursor.execute("INSERT INTO event_registrations (user_id, event_id) VALUES (?, ?)", (user_id, event_id))
        conn.commit()
        conn.close()
        return "Success", 200
    
    conn.close()
    return "Already Registered or Event Not Found", 200

@app.route('/profile')
def profile():
    if 'user_id' not in session: return redirect(url_for('login'))
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()
    
    user_info = cursor.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    orders = cursor.execute("SELECT * FROM orders WHERE user_id=?", (user_id,)).fetchall()
    
    # جلب الفعاليات المسجلة باسم الحقل لتعود نظيفة وتُعرض بأسمائها الأصلية في الـ HTML تلقائياً
    all_events = cursor.execute('''SELECT e.title, e.date_time, e.location 
                                   FROM events e 
                                   INNER JOIN event_registrations r ON e.id = r.event_id 
                                   WHERE r.user_id=?''', (user_id,)).fetchall()
    
    now = datetime.now()
    agenda = []         
    past_agenda = []    
    
    for event in all_events:
        try:
            raw_date = event['date_time'] # القراءة دايركت باسم الحقل
            if raw_date:
                event_time = datetime.strptime(raw_date, '%Y-%m-%d %H:%M')
                if event_time > now:
                    agenda.append(event)
                else:
                    past_agenda.append(event)
            else:
                agenda.append(event)
        except Exception as e:
            print(f"Error parsing date: {e}")
            agenda.append(event)

    conn.close()
    return render_template('profile.html', user=user_info, orders=orders, agenda=agenda, past_agenda=past_agenda)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)