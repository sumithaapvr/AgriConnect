from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
import mysql.connector
import secrets
import random
import string
import logging
from twilio.rest import Client
import os

app = Flask(__name__)

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.secret_key = secrets.token_hex(16)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Twilio configuration (replace with your actual credentials)
TWILIO_SID = 'your_twilio_account_sid'
TWILIO_AUTH_TOKEN = 'your_twilio_auth_token'
TWILIO_PHONE_NUMBER = 'your_twilio_phone_number'

# Database configuration
config = {
    'user': 'root',
    'password': 'Sumi@2004',
    'host': 'localhost',
    'database': 'sih',
    'raise_on_warnings': True
}

# Language support
LANGUAGES = {
    'ta': 'Tamil',
    'en': 'English',
    'ml': 'Malayalam',
    'te': 'Telugu',
    'kn': 'Kannada',
    'hi': 'Hindi'
}

def get_db_connection():
    return mysql.connector.connect(**config)

def is_authenticated():
    return 'authenticated' in session and session['authenticated']

def send_otp_via_sms(phone, otp):
    client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
    message_body = f"Your OTP code is {otp}"
    try:
        message = client.messages.create(
            body=message_body,
            from_=TWILIO_PHONE_NUMBER,
            to=phone
        )
        logging.info(f"OTP sent to {phone}. Message SID: {message.sid}")
    except Exception as e:
        logging.error(f"Failed to send OTP to {phone}. Error: {e}")

def store_otp_in_db(identifier, otp, is_email=False):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if is_email:
            cursor.execute('DELETE FROM otp_requests WHERE email = %s', (identifier,))
            cursor.execute('INSERT INTO otp_requests (email, otp, created_at) VALUES (%s, %s, NOW())', (identifier, otp))
        else:
            cursor.execute('DELETE FROM otp_requests WHERE phone = %s', (identifier,))
            cursor.execute('INSERT INTO otp_requests (phone, otp, created_at) VALUES (%s, %s, NOW())', (identifier, otp))
        conn.commit()
        logging.debug(f"OTP {otp} stored for {'email' if is_email else 'phone'}: {identifier}.")
    except mysql.connector.Error as err:
        logging.error(f"Database error: {err}")
    finally:
        cursor.close()
        conn.close()

def verify_otp_from_db(identifier, otp, is_email=False):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if is_email:
            cursor.execute('SELECT otp FROM otp_requests WHERE email = %s ORDER BY created_at DESC LIMIT 1', (identifier,))
        else:
            cursor.execute('SELECT otp FROM otp_requests WHERE phone = %s ORDER BY created_at DESC LIMIT 1', (identifier,))
        result = cursor.fetchone()
        logging.debug(f"OTP fetched from DB: {result}")
        return result and result['otp'] == otp
    except mysql.connector.Error as err:
        logging.error(f"Database error: {err}")
        return False
    finally:
        cursor.close()
        conn.close()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/select_language')
def select_language():
    lang_code = request.args.get('lang')
    if lang_code in LANGUAGES:
        session['language'] = lang_code
        return redirect(url_for('farmer_buyer_card'))
    return redirect(url_for('index'))

@app.route('/farmer_buyer_card')
def farmer_buyer_card():
    selected_language = session.get('language', 'en')
    if selected_language == 'ta':
        return render_template('farmer_card.html')
    return render_template('farmeren.html')

@app.route('/farmer')
def farmer():
    if not is_authenticated():
        return redirect(url_for('tamil_login'))
    return render_template('farmer_page.html')

@app.route('/buyer')
def buyer():
    if not is_authenticated():
        return redirect(url_for('buyer_login'))
    return render_template('buyer_page.html')

@app.route('/tamil_login', methods=['GET', 'POST'])
def tamil_login():
    if request.method == 'POST':
        phone = request.form.get('phone')
        otp = request.form.get('otp')
        
        logging.debug(f"Form Data: Phone={phone}, OTP={otp}")
        
        if verify_otp_from_db(phone, otp):
            session['authenticated'] = True
            logging.info(f"OTP verification successful for phone: {phone}")
            return redirect(url_for('product'))
        else:
            return render_template('tregister.html', error='Invalid OTP')
    
    return render_template('tamil_login.html')

@app.route('/english_login', methods=['GET', 'POST'])
def english_login():
    if request.method == 'POST':
        phone = request.form.get('phone')
        otp = request.form.get('otp')

        logging.debug(f"Form Data: Phone={phone}, OTP={otp}")
        
        if verify_otp_from_db(phone, otp):
            session['authenticated'] = True
            logging.info(f"OTP verification successful for phone: {phone}")
            return redirect(url_for('product'))
        else:
            logging.error(f"OTP verification failed for phone: {phone}")
            return render_template('english_login.html', error='Invalid OTP')

    return render_template('english_login.html')

# @app.route('/product')
# def product():
#     return render_template('product.html')

@app.route('/products')
def products():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT type, quantity, price, sample_photo_path FROM products')
    products = cursor.fetchall()  # Fetch all products
    cursor.close()
    conn.close()

    # Format the product data for rendering
    formatted_products = []
    for product in products:
        formatted_products.append({
            'type': product[0],
            'quantity': product[1],
            'price': product[2],
            'sample_photo_path': product[3]
        })

    return render_template('products.html', products=formatted_products)


@app.route('/buyer_login', methods=['GET', 'POST'])

def buyer_login():
    if request.method == 'POST':
        email = request.form['email']  # Change from phone to email
        otp = request.form['otp']
        
        logging.debug(f"Form Data: Email={email}, OTP={otp}")

        # Verify OTP based on email instead of phone
        if verify_otp_from_db(email, otp, is_email=True):
            session['authenticated'] = True
            logging.info(f"OTP verification successful for email: {email}")
            return redirect(url_for('buyer_things'))
        
        logging.error(f"OTP verification failed for email: {email}")
        return render_template('buyer_things.html', error='Invalid OTP')
    
    return render_template('buyer_login.html')
@app.route('/buyer_things')
def buyer_things():
    return render_template('buyer_things.html')


@app.route('/generate_otp', methods=['POST'])
def generate_otp():
    identifier = request.form['identifier']  # Can be phone or email
    otp = ''.join(random.choices(string.digits, k=6))
    
    logging.debug(f"Generated OTP: {otp} for identifier: {identifier}")
    
    if '@' in identifier:  # Check if it's an email
        store_otp_in_db(identifier, otp, is_email=True)
        # Optionally send OTP to email
    else:  # Assume it's a phone number
        send_otp_via_sms(identifier, otp)
        store_otp_in_db(identifier, otp)

    session['redirect_url'] = request.form.get('redirect_url', 'index')
    
    return redirect(url_for('otp_verification'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        product_type = request.form.get('type')
        quantity = request.form.get('quantity')
        price = request.form.get('price')
        sample_photo = request.files.get('sample_photo')

        # Initialize filename variable
        filename = None

        if sample_photo:
            # Ensure safe filenames
            filename = secure_filename(sample_photo.filename)
            
            # Create uploads directory if it doesn't exist
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            
            # Save the file to the uploads directory
            sample_photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        # Save the form data to the database (example)
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO products (type, quantity, price, sample_photo_path) VALUES (%s, %s,%s, %s)',
                           (product_type, quantity, price, filename))
            conn.commit()
        except mysql.connector.Error as err:
            logging.error(f"Database error: {err}")
        finally:
            cursor.close()
            conn.close()

        session['registered'] = True

    return render_template('tregister.html')


@app.route('/products')
def show_products():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch all product records
    cursor.execute('SELECT type, quantity, price, sample_photo_path FROM products')
    products = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('buyer_things.html', products=products)
# Order Product Route
@app.route('/order_product', methods=['GET', 'POST'])
def order_product():
    # Get quantity and price from URL
    product_quantity = int(request.args.get('product_quantity'))
    product_price = float(request.args.get('product_price'))  # Assuming price is a float

    if request.method == 'POST':
        # Get the form data
        name = request.form['name']
        address = request.form['address']
        phone = request.form['phone']
        quantity = int(request.form['quantity'])

        # Validate the quantity
        if quantity > product_quantity:
            flash(f"Please enter a quantity less than or equal to {product_quantity}.")
            return redirect(url_for('order_product', product_price=product_price, product_quantity=product_quantity))
        
        # Process order (you can add your order logic here)
        flash("Order placed successfully!")
        return redirect(url_for('products', product_price=product_price, product_quantity=product_quantity))

    return render_template('order_product.html', product_quantity=product_quantity, product_price=product_price)

# View Orders Route
@app.route('/orders')
def view_orders():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM orders ORDER BY order_date DESC")
        orders = cursor.fetchall()
    except Exception as e:
        orders = []
        flash(f"An error occurred: {e}")
    finally:
        conn.close()

    return render_template('orders.html', orders=orders)

@app.route('/process_order', methods=['POST'])
def process_order():
    # Extract form data
    name = request.form.get('name')
    address = request.form.get('address')
    phone = request.form.get('phone')
    quantity = int(request.form.get('quantity'))
    product_name = request.form.get('product_name')
    product_price = float(request.form.get('product_price'))

    # Calculate total price
    total_price = product_price * quantity

    # Render order summary page
    return render_template('order_summary.html', name=name, address=address, phone=phone,
                           product_name=product_name, quantity=quantity, total_price=total_price)

if __name__ == '__main__':
    app.run(debug=True) 