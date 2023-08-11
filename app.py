import os
import sqlite3
from flask import Flask, flash, render_template, request, redirect, url_for, session
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from google.auth.transport import requests

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Generate a random secret key
INSTANCE_PATH = os.path.join(os.getcwd(), 'instance')
DATABASE = os.path.join(INSTANCE_PATH, 'customer.db')
GOOGLE_CLIENT_ID = '230709683962-3n962ues65d5o6r9clhk8d4cenj27vfm.apps.googleusercontent.com'
GOOGLE_AUTH_REDIRECT_URI = 'https://customer-db.onrender.com/google/callback'

def create_database():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='customers'")
    table_exists = c.fetchone()

    if not table_exists:
        c.execute('''CREATE TABLE customers
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     name TEXT,
                     contact TEXT,
                     phone TEXT,
                     complaints TEXT,
                     solution TEXT,
                     cost TEXT,
                     part_payment TEXT,
                     balance_payment TEXT,
                     date TEXT,
                     remarks TEXT,
                     google_account_id TEXT)''')
    else:
        c.execute("PRAGMA table_info(customers)")
        columns = {column[1] for column in c.fetchall()}
        if 'google_account_id' not in columns:
            c.execute("ALTER TABLE customers ADD COLUMN google_account_id TEXT")

    conn.commit()
    conn.close()

@app.route('/')
def index():
    google_info = session.get('google_info')
    user_info = session.get('user_info')
    return render_template('index.html', google_info=google_info, user_info=user_info)

@app.route('/submit', methods=['POST'])
def submit():
    google_info = session.get('google_info')
    user_info = session.get('user_info')
    if not (google_info and user_info):
        flash('You need to log in with your Google account to add a customer.', 'error')
        return redirect(url_for('index'))

    name = request.form['name']
    contact = request.form['contact']
    phone = request.form['phone']
    complaints = request.form['complaints']
    solution = request.form['solution']
    cost = request.form['cost']
    part_payment = request.form['partPayment']
    balance_payment = request.form['balancePayment']
    date = request.form['date']
    remarks = request.form['remarks']
    google_account_id = user_info['sub']  # Get the unique Google account ID

    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('''INSERT INTO customers
                     (google_account_id, name, contact, phone, complaints, solution, cost, part_payment, balance_payment, date, remarks)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (google_account_id, name, contact, phone, complaints, solution, cost, part_payment, balance_payment, date, remarks))
        conn.commit()
        flash('Customer added successfully!', 'success')
    except sqlite3.Error as e:
        flash('Failed to add customer: {}'.format(str(e)), 'error')
    finally:
        conn.close()

    return redirect(url_for('index'))

@app.route('/google/callback')
def google_callback():
    code = request.args.get('code')
    flow = Flow.from_client_secrets_file(
        'client_secret.json',
        scopes=['openid', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile'],
        redirect_uri=GOOGLE_AUTH_REDIRECT_URI,
        state=session.get('google_auth_state', '')
    )

    try:
        flow.fetch_token(code=code)
        credentials = flow.credentials
        id_info = id_token.verify_oauth2_token(
            credentials._id_token,
            requests.Request(),
            GOOGLE_CLIENT_ID
        )
        if id_info:
            session['google_info'] = id_info
            session['user_info'] = id_info
            session['user_info']['picture'] = id_info.get('picture')
            print(id_info)  # Add this line
        else:
            flash('Google authentication failed.', 'error')
    except Exception as e:
        flash('Google authentication failed: {}'.format(str(e)), 'error')

    return redirect(url_for('index'))

@app.route('/google/logout')
def google_logout():
    session.pop('google_info', None)
    session.pop('user_info', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    create_database()
    app.run(debug=True, port=5000)
