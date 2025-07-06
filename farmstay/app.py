from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
import razorpay
import os
import csv
import json
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
from datetime import datetime, timedelta
from reportlab.pdfgen import canvas
from io import BytesIO

load_dotenv()

app = Flask(__name__, static_folder='public')
CORS(app)

PROMO_FILE = 'promocodes.csv'
BOOKING_FILE = 'bookings.json'

razorpay_key = os.getenv("RAZORPAY_KEY_ID")
razorpay_secret = os.getenv("RAZORPAY_KEY_SECRET")

if not razorpay_key or not razorpay_secret:
    raise ValueError("Missing Razorpay credentials in environment.")

razorpay_client = razorpay.Client(auth=(razorpay_key, razorpay_secret))

@app.route('/')
def home():
    return send_from_directory(app.static_folder, 'booking.html')

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory(app.static_folder, filename)

@app.route('/validate-promo', methods=['POST'])
def validate_promo():
    try:
        data = request.get_json()
        entered_code = data.get('code', '').strip().upper()
        discount = 0
        valid = False

        if os.path.exists(PROMO_FILE):
            with open(PROMO_FILE, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['code'].strip().upper() == entered_code:
                        discount = int(row['discount'])
                        valid = True
                        break

        return jsonify({'valid': valid, 'discount': discount})
    except Exception as e:
        return jsonify({'valid': False, 'error': str(e)}), 500

@app.route('/create-order', methods=['POST'])
def create_order():
    try:
        data = request.get_json()
        amount = int(float(data.get('amount', 0))) * 100

        if amount <= 0:
            return jsonify({'error': 'Invalid amount'}), 400

        payment = razorpay_client.order.create({
            "amount": amount,
            "currency": "INR",
            "payment_capture": 1
        })

        return jsonify(payment)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/confirm-booking', methods=['POST'])
def confirm_booking():
    try:
        data = request.get_json()

        required = ['name', 'email', 'phone', 'checkin', 'checkout', 'guests']
        for field in required:
            if not data.get(field):
                return jsonify({'status': 'error', 'message': f'Missing: {field}'}), 400

        if '@' not in data['email']:
            return jsonify({'status': 'error', 'message': 'Invalid email'}), 400

        try:
            amount = int(float(data.get('amount', 0)))
        except:
            return jsonify({'status': 'error', 'message': 'Invalid amount'}), 400

        if amount < 0:
            return jsonify({'status': 'error', 'message': 'Amount must be non-negative'}), 400

        checkin_date = datetime.strptime(data['checkin'], '%Y-%m-%d')
        checkout_date = datetime.strptime(data['checkout'], '%Y-%m-%d')
        if checkout_date <= checkin_date:
            return jsonify({'status': 'error', 'message': 'Checkout must be after checkin'}), 400

        bookings = []
        if os.path.exists(BOOKING_FILE):
            try:
                with open(BOOKING_FILE, 'r') as f:
                    bookings = json.load(f)
            except json.JSONDecodeError:
                bookings = []

        bookings.append(data)
        with open(BOOKING_FILE, 'w') as f:
            json.dump(bookings, f, indent=2)

        sender_email = os.getenv("SMTP_EMAIL")
        sender_pass = os.getenv("SMTP_PASSWORD")
        recipient = data['email']

        if not sender_email or not sender_pass:
            raise Exception("SMTP credentials missing")

        subject = "Booking Confirmation - GreenOBird Farmstay"
        body = f"""
Hello {data['name']},

Thank you for booking GreenOBird Farmstay!
Check-In: {data['checkin']}
Check-Out: {data['checkout']}
Guests: {data['guests']}
Amount Paid: ₹{amount}

We look forward to hosting you!

Regards,
GreenOBird Team
        """

        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = recipient

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, sender_pass)
            smtp.send_message(msg)

        return jsonify({'status': 'success', 'message': 'Booking confirmed and email sent.'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/bookings')
def list_bookings():
    if not os.path.exists(BOOKING_FILE):
        return jsonify([])
    with open(BOOKING_FILE, 'r') as f:
        return jsonify(json.load(f))

@app.route('/invoice/<email>')
def get_invoice(email):
    if not os.path.exists(BOOKING_FILE):
        return "No bookings found", 404

    with open(BOOKING_FILE, 'r') as f:
        bookings = json.load(f)

    booking = next((b for b in bookings if b['email'].lower() == email.lower()), None)
    if not booking:
        return "Booking not found", 404

    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    p.setFont("Helvetica", 12)
    p.drawString(100, 800, "GreenOBird Farmstay - Booking Invoice")
    p.drawString(100, 780, f"Name: {booking['name']}")
    p.drawString(100, 760, f"Email: {booking['email']}")
    p.drawString(100, 740, f"Check-In: {booking['checkin']}")
    p.drawString(100, 720, f"Check-Out: {booking['checkout']}")
    p.drawString(100, 700, f"Guests: {booking['guests']}")
    p.drawString(100, 680, f"Amount Paid: ₹{booking['amount']}")
    p.drawString(100, 660, f"Payment ID: {booking.get('razorpay_payment_id', 'N/A')}")
    p.showPage()
    p.save()

    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='invoice.pdf', mimetype='application/pdf')

@app.route('/booked-dates')
def get_booked_dates():
    if not os.path.exists(BOOKING_FILE):
        return jsonify([])

    try:
        with open(BOOKING_FILE, 'r') as f:
            bookings = json.load(f)
    except Exception:
        return jsonify([])

    blocked = set()

    for booking in bookings:
        checkin = booking.get('checkin')
        checkout = booking.get('checkout')
        try:
            start = datetime.strptime(checkin, '%Y-%m-%d')
            end = datetime.strptime(checkout, '%Y-%m-%d')
            while start < end:
                blocked.add(start.strftime('%Y-%m-%d'))
                start += timedelta(days=1)
        except Exception as e:
            print(f"Error parsing booking: {booking} — {e}")
            continue

    return jsonify(sorted(list(blocked)))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
