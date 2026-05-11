from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
import json

app = Flask(__name__)
app.secret_key = 'mostdam_2026'

# إعدادات أمان إضافية للجلسة (Sessions)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# --- 1. إعداد قاعدة البيانات بشكل ديناميكي ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'platform.db')

def get_db_connection():
    """دالة لفتح اتصال بقاعدة البيانات مع دعم الوصول للبيانات كقاموس"""
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

init_db()

# --- 2. مسارات النظام (Routes) ---

@app.route('/')
def index():
    user_name = session.get('user_name')
    return render_template('index.html', user_name=user_name)

@app.route('/subscribe', methods=['POST'])
def subscribe():
    # تنظيف الإيميل من المسافات الزائدة
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
            # 1. إدخال البيانات في القاعدة
            cursor.execute("INSERT INTO users (full_name, email, phone, city, password) VALUES (?, ?, ?, ?, ?)", 
               (name, email, phone, city, password))
            
            # 2. جلب ID المستخدم الذي تم إنشاؤه للتو
            user_id = cursor.lastrowid
            
            conn.commit()
            conn.close()
            
            # 3. الربط السحري: تسجيل دخول المستخدم تلقائياً
            session['user_id'] = user_id
            session['user_name'] = name
            
            # 4. التوجيه فوراً للصفحة الرئيسية
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
        
        # البحث في القاعدة: إذا وجدت البيانات يدخل، وإذا لم توجد يرفض
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
    if 'user_id' not in session: return redirect(url_for('login'))
    event_id = request.form.get('event_id')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO event_registrations (user_id, event_id) VALUES (?, ?)", (session['user_id'], event_id))
    conn.commit()
    conn.close()
    return "<script>alert('تم التسجيل في الفعالية'); window.location.href='/profile';</script>"

@app.route('/profile')
def profile():
    if 'user_id' not in session: return redirect(url_for('login'))
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()
    
    user_info = cursor.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    orders = cursor.execute("SELECT product_name, amount, order_date, status FROM orders WHERE user_id=?", (user_id,)).fetchall()
    agenda = cursor.execute('''SELECT e.title, e.date_time, e.location 
                              FROM events e 
                              JOIN event_registrations r ON e.id = r.event_id 
                              WHERE r.user_id=?''', (user_id,)).fetchall()
    
    conn.close()
    return render_template('profile.html', user=user_info, orders=orders, agenda=agenda)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    # دعم PORT الخاص بالاستضافة والتشغيل المحلي مع تفعيل وضع التطوير (debug=True) لرؤية الأخطاء
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)