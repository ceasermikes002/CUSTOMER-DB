import flask
from flask import Flask, flash, render_template, request, redirect, url_for, session
import sqlite3
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from google.auth.transport import requests
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'
INSTANCE_PATH = os.path.join(os.getcwd(), 'instance')
DATABASE = os.path.join(INSTANCE_PATH, 'customer.db')
GOOGLE_CLIENT_ID = '230709683962-3n962ues65d5o6r9clhk8d4cenj27vfm.apps.googleusercontent.com'
GOOGLE_CLIENT_SECRET = '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'
GOOGLE_AUTH_REDIRECT_URI = 'http://localhost:8080/google/callback'

# Create the database and table if they don't exist
def create_database():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    # Check if the customers table exists
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
        # Check if the google_account_id column exists
        c.execute("PRAGMA table_info(customers)")
        columns = [column[1] for column in c.fetchall()]
        if 'google_account_id' not in columns:
            c.execute("ALTER TABLE customers ADD COLUMN google_account_id TEXT")

    conn.commit()
    conn.close()


# Route for the index page
@app.route('/')
def index():
    google_info = session.get('google_info')
    user_info = session.get('user_info')
    if google_info and user_info:
        return render_template('index.html', google_info=google_info)
    else:
        return render_template('index.html')



# Route for saving the customer form data
@app.route('/submit', methods=['POST'])
def submit():
    google_info = session.get('google_info')
    user_info = session.get('user_info')
    if google_info and user_info:
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

        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        try:
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
    else:
        flash('You need to log in with your Google account to add a customer.', 'error')

    return redirect(url_for('index'))


# Route for the search page
# Route for the search page
@app.route('/search', methods=['GET', 'POST'])
def search():
    google_info = session.get('google_info')
    user_info = session.get('user_info')
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
        return render_template('search.html', google_info=google_info)
    else:
        return render_template('search.html', google_info=None)  # Pass google_info as None




# Route for the remove page
@app.route('/remove', methods=['GET', 'POST'])
def remove():
    google_info = session.get('google_info')
    user_info = session.get('user_info')
    if google_info and user_info:
        if request.method == 'POST':
            search_query = request.form['search']
            conn = sqlite3.connect(DATABASE)
            c = conn.cursor()
            c.execute("SELECT * FROM customers WHERE name LIKE ? OR phone LIKE ?",
                      ('%' + search_query + '%', '%' + search_query + '%'))
            results = c.fetchall()
            conn.close()
            return render_template('remove.html', results=results, google_info=google_info)
        return render_template('remove.html', google_info=google_info, user_info=user_info)  # Pass user_info variable
    else:
        return render_template('remove.html', google_info=None)  # Pass google_info as None




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
    session['google_auth_state'] = state  # Store the state value in the session
    return redirect(authorization_url)


@app.route('/google/callback')
def google_callback():
    code = request.args.get('code')
    flow = Flow.from_client_secrets_file(
        'client_secret.json',
        scopes=['openid', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile'],
        redirect_uri=GOOGLE_AUTH_REDIRECT_URI,
        state=session.get('google_auth_state')  # Use get() with a fallback value
    )
    flow.fetch_token(code=code)
    credentials = flow.credentials
    id_info = id_token.verify_oauth2_token(
        credentials._id_token,
        requests.Request(),
        GOOGLE_CLIENT_ID
    )
    if id_info:
        # Authentication successful, store user information in session
        session['google_info'] = id_info

        # Add profile picture to user_info
        session['user_info'] = id_info
        session['user_info']['picture'] = id_info.get('picture')

        print(id_info)  # Add this line

    else:
        # Authentication failed
        flash('Google authentication failed.', 'error')

    return redirect(url_for('index'))




@app.route('/google/logout')
def google_logout():
    session.pop('google_info', None)
    session.pop('user_info', None)  # Add this line
    return redirect(url_for('index'))



if __name__ == '__main__':
    create_database()
    app.run(host='0.0.0.0', port=os.environ.get('PORT', 5000))


