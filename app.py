from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
import json

app = Flask(__name__)
app.secret_key = 'mostdam_2026'

# --- 1. إعداد قاعدة البيانات ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'platform.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
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

    # جدول المنتجات (للمتجر)
    cursor.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        price REAL NOT NULL,
        stock INTEGER DEFAULT 0
    )''')

    # جدول الطلبات (مشتريات المتجر)
    cursor.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        product_name TEXT,
        amount REAL,
        order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'قيد المراجعة',
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')

    # جدول الفعاليات (البرامج)
    cursor.execute('''CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        date_time TEXT,
        location TEXT
    )''')

    # جدول تسجيل المستخدمين في الفعاليات (الأجندة)
    cursor.execute('''CREATE TABLE IF NOT EXISTS event_registrations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        event_id INTEGER,
        reg_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (event_id) REFERENCES events (id)
    )''')

    # جدول النشرة البريدية (الإضافة الجديدة)
    cursor.execute('''CREATE TABLE IF NOT EXISTS newsletter (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        subscription_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    conn.close()

init_db()

# --- 2. مسارات النظام (Routes) ---

@app.route('/')
def index():
    user_name = session.get('user_name')
    return render_template('index.html', user_name=user_name)

# --- مسار النشرة البريدية الجديد ---
@app.route('/subscribe', methods=['POST'])
def subscribe():
    email = request.form.get('subscriber_email')
    if email:
        conn = sqlite3.connect(DB_PATH)
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

# --- نظام الحسابات ---
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        password = request.form.get('password')
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO users (full_name, email, password) VALUES (?, ?, ?)', (full_name, email, password))
            conn.commit()
            return redirect(url_for('login'))
        except:
            return "<script>alert('الايميل مسجل مسبقاً'); window.location.href='/signup';</script>"
        finally: conn.close()
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
        user = cursor.fetchone()
        conn.close()
        if user:
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            return redirect(url_for('index'))
    return render_template('login.html')

# --- نظام المتجر ---
@app.route('/store')
def store():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products")
    all_products = cursor.fetchall()
    conn.close()
    return render_template('store.html', products=all_products)

@app.route('/checkout', methods=['POST'])
def checkout():
    if 'user_id' not in session: return redirect(url_for('login'))
    cart_data = request.form.get('cart_data')
    items = json.loads(cart_data)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for item in items:
        cursor.execute("INSERT INTO orders (user_id, product_name, amount) VALUES (?, ?, ?)",
                       (session['user_id'], item['name'], item['price']))
    conn.commit()
    conn.close()
    return "<script>alert('تم الشراء بنجاح'); window.location.href='/profile';</script>"

# --- نظام الفعاليات (البرامج) ---
@app.route('/programs')
def programs():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events")
    all_events = cursor.fetchall()
    conn.close()
    return render_template('programs.html', events=all_events)

@app.route('/register_event', methods=['POST'])
def register_event():
    if 'user_id' not in session: return redirect(url_for('login'))
    event_id = request.form.get('event_id')
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO event_registrations (user_id, event_id) VALUES (?, ?)", (session['user_id'], event_id))
    conn.commit()
    conn.close()
    return "<script>alert('تم التسجيل في الفعالية'); window.location.href='/profile';</script>"

# --- الملف الشخصي ---
@app.route('/profile')
def profile():
    if 'user_id' not in session: return redirect(url_for('login'))
    user_id = session['user_id']
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # جلب بيانات المستخدم
    cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user_info = cursor.fetchone()
    
    # جلب المشتريات
    cursor.execute("SELECT product_name, amount, order_date, status FROM orders WHERE user_id=?", (user_id,))
    orders = cursor.fetchall()
    
    # جلب الأجندة (الفعاليات المسجلة)
    cursor.execute('''SELECT e.title, e.date_time, e.location 
                      FROM events e 
                      JOIN event_registrations r ON e.id = r.event_id 
                      WHERE r.user_id=?''', (user_id,))
    agenda = cursor.fetchall()
    
    conn.close()
    return render_template('profile.html', user=user_info, orders=orders, agenda=agenda)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)