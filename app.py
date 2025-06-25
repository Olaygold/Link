from flask import Flask, request, redirect, render_template_string, session, g
import psycopg2
import psycopg2.extras
import os

# --- Configuration ---
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "secret123")
DATABASE_URL = os.environ.get("DATABASE_URL", "dbname=liink_db user=liink_db_user password=bBozyyyaARlKGeElmudpAmcADsqFaths host=dpg-d1dulomr433s73fr9da0-a port=5432")

# --- Database Connection ---
def get_db():
    if 'db' not in g:
        g.db = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()




def init_db():
    db = get_db()
    cur = db.cursor()

    # Create table if it doesn't exist
    cur.execute('''
        CREATE TABLE IF NOT EXISTS links (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Add missing columns (views, clicks) if they don't exist
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='links'")
    columns = [row['column_name'] for row in cur.fetchall()]

    if 'views' not in columns:
        cur.execute("ALTER TABLE links ADD COLUMN views INTEGER DEFAULT 0")
    if 'clicks' not in columns:
        cur.execute("ALTER TABLE links ADD COLUMN clicks INTEGER DEFAULT 0")

    db.commit()
    cur.close()


# --- Routes ---
@app.route('/')
def home():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM links")
    links = cur.fetchall()
    if not session.get('admin'):
        cur.execute("UPDATE links SET views = views + 1")
        db.commit()
    cur.close()
    return render_template_string(public_html, links=links, is_admin=session.get('admin'))

@app.route('/click/<int:link_id>')
def click(link_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE links SET clicks = clicks + 1 WHERE id = %s", (link_id,))
    cur.execute("SELECT url FROM links WHERE id = %s", (link_id,))
    url = cur.fetchone()['url']
    db.commit()
    cur.close()
    return redirect(url)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = ''
    if request.method == 'POST':
        if request.form['username'] == 'admin' and request.form['password'] == 'admin':
            session['admin'] = True
            return redirect('/dashboard')
        else:
            error = 'Invalid credentials'
    return render_template_string(login_html, error=error)

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect('/login')

@app.route('/dashboard')
def dashboard():
    if not session.get('admin'):
        return redirect('/login')
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM links")
    links = cur.fetchall()
    cur.close()
    return render_template_string(dashboard_html, links=links)

@app.route('/add', methods=['POST'])
def add():
    if not session.get('admin'):
        return redirect('/login')
    title = request.form['title']
    url = request.form['url']
    db = get_db()
    cur = db.cursor()
    cur.execute("INSERT INTO links (title, url) VALUES (%s, %s)", (title, url))
    db.commit()
    cur.close()
    return redirect('/dashboard')

@app.route('/delete/<int:link_id>')
def delete(link_id):
    if not session.get('admin'):
        return redirect('/login')
    db = get_db()
    cur = db.cursor()
    cur.execute("DELETE FROM links WHERE id = %s", (link_id,))
    db.commit()
    cur.close()
    return redirect('/dashboard')

@app.route('/edit/<int:link_id>', methods=['POST'])
def edit(link_id):
    if not session.get('admin'):
        return redirect('/login')
    title = request.form['title']
    url = request.form['url']
    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE links SET title = %s, url = %s WHERE id = %s", (title, url, link_id))
    db.commit()
    cur.close()
    return redirect('/dashboard')

# ===============================
# ========== HTMLs =============
# ===============================

login_html = '''
<!DOCTYPE html>
<html><head><title>Login</title></head>
<body style="font-family:sans-serif;text-align:center;padding-top:50px;">
  <h2>Admin Login</h2>
  {% if error %}<p style="color:red;">{{ error }}</p>{% endif %}
  <form method="post">
    <input name="username" placeholder="Username"><br><br>
    <input name="password" type="password" placeholder="Password"><br><br>
    <button type="submit">Login</button>
  </form>
</body></html>
'''

dashboard_html = '''
<!DOCTYPE html>
<html><head><title>Dashboard</title></head>
<body style="font-family:sans-serif;padding:20px;">
  <h2>Admin Dashboard</h2>
  <a href="/logout">Logout</a><br><br>
  <form method="post" action="/add">
    <input name="title" placeholder="Topic Title" required>
    <input name="url" placeholder="Link URL" required>
    <button type="submit">Add Topic</button>
  </form>
  <hr>
  <h3>Topics</h3>
  {% for link in links %}
    <form method="post" action="/edit/{{ link.id }}">
      <input name="title" value="{{ link.title }}">
      <input name="url" value="{{ link.url }}">
      <button type="submit">Update</button>
      <a href="/delete/{{ link.id }}" onclick="return confirm('Delete this topic?')">Delete</a><br>
      <small>Views: {{ link.views }} | Clicks: {{ link.clicks }}</small>
    </form>
    <hr>
  {% endfor %}
</body></html>
'''

public_html = '''
<!DOCTYPE html>
<html>
<head>
  <title>Useful Topics</title>
  <style>
    body { font-family: sans-serif; background: #f0f0f0; padding: 20px; }
    .topic { background: white; padding: 15px; margin-bottom: 15px; border-radius: 8px; box-shadow: 0 0 5px #ccc; }
    .title { font-size: 20px; font-weight: bold; }
    a { color: blue; text-decoration: none; }
  </style>
</head>
<body>
  <h2>🔗 Useful Topics</h2>
  {% for link in links %}
    <div class="topic">
      <div class="title">{{ link.title }}</div>
      <a href="/click/{{ link.id }}" target="_blank">👉 Click to view</a><br>
      {% if is_admin %}
        <small>Views: {{ link.views }}, Clicks: {{ link.clicks }}</small>
      {% endif %}
    </div>
  {% endfor %}
</body>
</html>
'''

# --- Run App ---
if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True)
