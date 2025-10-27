from flask import Flask, render_template, jsonify, request, session, redirect, url_for, flash
import requests
import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId

app = Flask(__name__)

app.secret_key = '7d9cd4998bf5c3034f9065dd8a0f1ccb759debde8757e219bcff6a8ef5151437bb5608e458d3bd78faf1592b032b7f2033c2fc8eb3e0a38f8a0f2b72643d9bf7'

# database config
client = MongoClient('mongodb+srv://chaktomukDigitalDb:Www.2473%40.com@cluster0.0srcq1b.mongodb.net/')
db = client['shop_db']
customers = db['customers']
orders = db['orders']

# Telegram config
token = "8420874385:AAG89KOYSxNNtLQCqrT3Uwtc3U6IxKhikoQ"
chatId = "1084261917"
telegram_url = f"https://api.telegram.org/bot{token}/sendMessage"

# Email config
port = 465
smtp_server = "smtp.gmail.com"
sender_email = "rornsokhengnaa@gmail.com"
password = "wadl utfb agpx mnih"


# ============ Guard Routing ============

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'email' not in session:
            flash('Please login first', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def guest_required(f):
    """Decorator to prevent logged-in users from accessing auth pages"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'email' in session:
            flash('You are already logged in', 'info')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function


# ============ API ENDPOINT ============

@app.route('/api/check-session')
def check_session():
    """Check if user is logged in - for Vue.js"""
    if 'email' in session:
        user = customers.find_one({'email': session['email']})
        return jsonify({
            'logged_in': True,
            'email': session['email'],
            'fullname': user.get('fullname', '') if user else ''
        })
    return jsonify({'logged_in': False})



# ============ PAGE ROUTE ============

@app.get("/")
@app.get("/home")
def home():
    """Home page with products from Fake Store API"""
    product_list = []
    api_url = 'https://fakestoreapi.com/products'
    try:
        r = requests.get(api_url, timeout=10)
        if r.status_code == 200:
            product_list = r.json()
    except Exception as e:
        print(f"Error fetching products: {e}")
    return render_template('home.html', product_list=product_list)


@app.get("/product-detail/<int:pro_id>")
def product_detail(pro_id):
    """Product detail page"""
    product = {}
    api_url = f"https://fakestoreapi.com/products/{pro_id}"
    try:
        r = requests.get(api_url, timeout=10)
        if r.status_code == 200:
            product = r.json()
    except Exception as e:
        print(f"Error fetching product: {e}")
        flash('Product not found', 'danger')
    return render_template('product_detail.html', product=product)


@app.get('/cart')
@login_required
def cart():
    """Cart page"""
    return render_template('cart.html')


@app.get('/checkout')
@login_required
def checkout():
    """Checkout page"""
    return render_template('checkout.html')


@app.get('/about')
def about():
    """About page"""
    return render_template('about.html')


@app.get('/contact')
def contact():
    """Contact page"""
    return render_template('contact.html')


# ============ AUTHENTICATION ROUTE ============

@app.route('/login', methods=['GET', 'POST'])
@guest_required 
def login():
    """Login and Register page (auth.html)"""
    if request.method == 'POST':
        email = request.form.get('email')
        pwd = request.form.get('password')
        
        if not email or not pwd:
            flash('Email and password required', 'danger')
            return redirect(url_for('login'))
        
        user = customers.find_one({'email': email})
        
        if user and check_password_hash(user['password'], pwd):
            session['email'] = email
            session.permanent = True  
            flash('Welcome back!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password', 'danger')
            return redirect(url_for('login'))
    
    return render_template('auth.html')


@app.route('/register', methods=['POST'])
@guest_required  
def register():
    """User registration"""
    fullname = request.form.get('fullname')
    email = request.form.get('email')
    pwd = request.form.get('password')
    
    if not email or not pwd:
        flash('Email and password required', 'danger')
        return redirect(url_for('login'))
    
    if len(pwd) < 6:
        flash('Password must be at least 6 characters', 'danger')
        return redirect(url_for('login'))
    
    if customers.find_one({'email': email}):
        flash('Email already registered', 'danger')
        return redirect(url_for('login'))
    
    try:
        customers.insert_one({
            'fullname': fullname,
            'email': email,
            'password': generate_password_hash(pwd),
            'created_at': datetime.now()
        })
        flash('Account created successfully! Please login', 'success')
    except Exception as e:
        print(f"Registration error: {e}")
        flash('Registration failed. Please try again', 'danger')
    
    return redirect(url_for('login'))


@app.route('/logout')
def logout():
    """User logout"""
    session.clear()
    flash('Logged out successfully', 'info')
    return redirect(url_for('home'))


@app.route('/profile')
@login_required 
def profile():
    """User profile page with order history"""
    user = customers.find_one({'email': session['email']})
    
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('logout'))
    
    user_orders = list(orders.find({'email': session['email']}).sort('created_at', -1))
    
    return render_template('profile.html', user=user, orders=user_orders)


# ============ ORDER HELPER ============

def send_telegram_notification(order_data):
    """Send order notification to Telegram"""
    try:
        data = order_data
        name = f"{data.get('customer', {}).get('firstName', '')} {data.get('customer', {}).get('lastName', '')}"
        street = data.get("address", {}).get("street", "")
        city = data.get("address", {}).get("city", "")
        email = data.get("customer", {}).get("email", "")
        phone = data.get("customer", {}).get("phone", "")
        payment = data.get("payment", {}).get("method", "")
        items = data.get("items", [])

        message = (
            f"<b>🛒 ទទួលបានការបញ្ជាទិញថ្មី</b>\n"
            f"<b>ឈ្មោះ៖</b> {name}\n"
            f"<b>អាស័យដ្ឋាន៖</b> {street} {city}\n"
            f"<b>អ៊ីមែល៖</b> {email}\n"
            f"<b>លេខទូរស័ព្ទ៖</b> <code>{phone}</code>\n"
            f"<b>បង់តាមរយះ៖</b> {payment}\n"
            f"<b>==================================</b>\n"
        )

        total_price = 0
        if items:
            message += "<b>📦 ទំនិញ:</b>\n"
            for item in items:
                qty = item.get('qty', 1)
                price = item.get('price', 0)
                subtotal = qty * price
                total_price += subtotal
                message += (
                    f"<b>ឈ្មោះទំនិញ៖</b> {item.get('title', '')} x{qty}\n"
                    f"<b>តម្លៃ៖</b> {price}$\n"
                    f"<b>តម្លៃសរុប៖</b> {subtotal}$\n\n"
                )
            message += f"<b>💰 តម្លៃសរុបទាំងអស់៖</b> {total_price}$\n"

        payload = {
            "chat_id": chatId,
            "text": message,
            "parse_mode": "HTML"
        }
        
        response = requests.post(telegram_url, json=payload, timeout=10)
        return response.status_code == 200, total_price
    except Exception as e:
        print(f"Telegram error: {e}")
        return False, 0


def send_order_email(order_data, total_price):
    """Send order confirmation email"""
    try:
        data = order_data
        name = f"{data.get('customer', {}).get('firstName', '')} {data.get('customer', {}).get('lastName', '')}"
        street = data.get("address", {}).get("street", "")
        city = data.get("address", {}).get("city", "")
        email = data.get("customer", {}).get("email", "")
        phone = data.get("customer", {}).get("phone", "")
        payment = data.get("payment", {}).get("method", "")
        items = data.get("items", [])

        email_message = f"""
        <b>🛍️ វិកាយប័ត្រការបញ្ជាទិញ</b><br>
        <hr>
        <table>
        <tr><td><b>👤 ឈ្មោះ:</b></td><td>{name}</td></tr>
        <tr><td><b>🏠 អាស័យដ្ឋាន:</b></td><td>{street} {city}</td></tr>
        <tr><td><b>📧 អ៊ីមែល:</b></td><td>{email}</td></tr>
        <tr><td><b>📞 លេខទូរស័ព្ទ:</b></td><td>{phone}</td></tr>
        <tr><td><b>💳 បង់តាមរយៈ:</b></td><td>{payment}</td></tr>
        </table>
        <hr>
        <b>📦 ទំនិញដែលបានបញ្ជាទិញ:</b><br>
        <table border="1" cellpadding="5" cellspacing="0">
        <tr>
            <th>ឈ្មោះទំនិញ</th>
            <th>ចំនួន</th>
            <th>តម្លៃ</th>
            <th>តម្លៃសរុប</th>
        </tr>
        """

        for item in items:
            qty = item.get('qty', 1)
            price = item.get('price', 0)
            subtotal = qty * price
            email_message += f"<tr><td>{item.get('title', '')}</td><td>{qty}</td><td>{price}$</td><td>{subtotal}$</td></tr>"

        email_message += f"""
        <tr>
            <td colspan="3" align="right"><b>💰 តម្លៃសរុបទាំងអស់:</b></td>
            <td><b>{total_price}$</b></td>
        </tr>
        </table>
        <hr>
        <b>🙏 អរគុណសម្រាប់ការបញ្ជាទិញ!</b>
        """

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "វិកាយប័ត្រការបញ្ជាទិញ"
        msg["From"] = sender_email
        msg["To"] = email
        msg.attach(MIMEText(email_message, "html", "utf-8"))

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, email, msg.as_string())
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False


# ============ ORDER ROUTE ============

# @app.post("/order")
# def create_order():
#     """Create order for guest users (not saved to database)"""
#     data = request.json
#     if not data:
#         return jsonify({"error": "Invalid data"}), 400

#     telegram_success, total_price = send_telegram_notification(data)
#     email_success = send_order_email(data, total_price)

#     if telegram_success:
#         return jsonify({"status": "success", "message": "Order placed successfully"})
#     else:
#         return jsonify({"status": "error", "message": "Failed to place order"}), 500


@app.post("/order-logged")
@login_required
def create_order_logged():
    """Create order for logged-in users (saves to database)"""
    data = request.json
    if not data:
        return jsonify({"error": "Invalid data"}), 400

    telegram_success, total_price = send_telegram_notification(data)
    email_success = send_order_email(data, total_price)

    try:
        orders.insert_one({
            'email': session['email'],
            'order_data': data,
            'total': total_price,
            'status': 'pending',
            'created_at': datetime.now()
        })
    except Exception as e:
        print(f"Database error: {e}")

    if telegram_success:
        return jsonify({"status": "success", "message": "Order placed successfully"})
    else:
        return jsonify({"status": "error", "message": "Failed to place order"}), 500


# ============ ERROR HANDLER ============

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

