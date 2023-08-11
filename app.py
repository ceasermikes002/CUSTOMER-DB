import os
import sqlite3
from flask import Flask, flash, render_template, request, redirect, url_for, session
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from google.auth.transport import requests

app = Flask(__name__)

# Set a secure secret key for session management
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your_default_secret_key')

# Database Configuration
INSTANCE_PATH = os.path.join(os.getcwd(), 'instance')
DATABASE = os.path.join(INSTANCE_PATH, 'customer.db')
GOOGLE_CLIENT_ID = '230709683962-3n962ues65d5o6r9clhk8d4cenj27vfm.apps.googleusercontent.com'
GOOGLE_AUTH_REDIRECT_URI = 'https://customer-db.onrender.com/google/callback'

# Function to create the database and customers table
def create_database():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS customers
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

    conn.commit()
    conn.close()

# Route for the index page
@app.route('/')
def index():
    google_info = session.get('google_info')
    user_info = session.get('user_info')
    return render_template('index.html', google_info=google_info, user_info=user_info)

# Route for saving customer form data
@app.route('/submit', methods=['POST'])
def submit():
    google_info = session.get('google_info')
    user_info = session.get('user_info')
    if google_info and user_info:
        data = {field: request.form[field] for field in request.form}
        data['google_account_id'] = user_info['sub']

        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        try:
            c.execute('''INSERT INTO customers
                         (google_account_id, name, contact, phone, complaints, solution, cost, part_payment, balance_payment, date, remarks)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (data['google_account_id'], data['name'], data['contact'], data['phone'], data['complaints'],
                       data['solution'], data['cost'], data['partPayment'], data['balancePayment'], data['date'], data['remarks']))
            conn.commit()
            flash('Customer added successfully!', 'success')
        except sqlite3.Error as e:
            flash('Failed to add customer: {}'.format(str(e)), 'error')
        finally:
            conn.close()
    else:
        flash('You need to log in with your Google account to add a customer.', 'error')

    return redirect(url_for('index'))

# Route for searching customers
@app.route('/search', methods=['GET', 'POST'])
def search():
    google_info = session.get('google_info')
    user_info = session.get('user_info')
    results = []

    if google_info and user_info:
        if request.method == 'POST':
            search_query = request.form['search']
            conn = sqlite3.connect(DATABASE)
            c = conn.cursor()
            c.execute("SELECT * FROM customers WHERE name LIKE ? OR phone LIKE ? OR complaints LIKE ?",
                      ('%' + search_query + '%', '%' + search_query + '%', '%' + search_query + '%'))
            results = c.fetchall()
            conn.close()

    return render_template('search.html', results=results, google_info=google_info)

# Route for removing customers
@app.route('/remove', methods=['GET', 'POST'])
def remove():
    google_info = session.get('google_info')
    user_info = session.get('user_info')
    results = []

    if google_info and user_info:
        if request.method == 'POST':
            search_query = request.form['search']
            conn = sqlite3.connect(DATABASE)
            c = conn.cursor()
            c.execute("SELECT * FROM customers WHERE name LIKE ? OR phone LIKE ?",
                      ('%' + search_query + '%', '%' + search_query + '%'))
            results = c.fetchall()
            conn.close()

    return render_template('remove.html', results=results, google_info=google_info, user_info=user_info)

# Route for deleting a customer
@app.route('/delete/<int:customer_id>', methods=['POST'])
def delete(customer_id):
    google_info = session.get('google_info')
    user_info = session.get('user_info')
    if google_info and user_info:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
        conn.commit()
        conn.close()
        flash('Customer removed successfully!', 'success')
    else:
        flash('You need to log in with your Google account to delete a customer.', 'error')

    return redirect(url_for('remove'))

# Google OAuth routes
@app.route('/google/login', endpoint='google_login')
def google_login():
    flow = Flow.from_client_secrets_file(
        'client_secret.json',
        scopes=['openid', 'email', 'profile'],
        redirect_uri=GOOGLE_AUTH_REDIRECT_URI
    )
    authorization_url, state = flow.authorization_url(access_type='offline')
    session['google_auth_state'] = state
    return redirect(authorization_url)

@app.route('/google/callback')
def google_callback():
    code = request.args.get('code')
    flow = Flow.from_client_secrets_file(
        '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',
        scopes=['openid', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile'],
        redirect_uri=GOOGLE_AUTH_REDIRECT_URI,
        state=session.get('google_auth_state', '')
    )
    flow.fetch_token(code=code)
    credentials = flow.credentials
    id_info = id_token.verify_oauth2_token(
        credentials._id_token,
        requests.Request(),
        GOOGLE_CLIENT_ID
    )
    if id_info:
        session['google_info'] = id_info
        session['user_info'] = {'sub': id_info.get('sub'), 'picture': id_info.get('picture')}
    else:
        flash('Google authentication failed.', 'error')

    return redirect(url_for('index'))

@app.route('/google/logout')
def google_logout():
    session.pop('google_info', None)
    session.pop('user_info', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    create_database()
    # Use Gunicorn for deployment
    app.run(debug=True, port=5000)
