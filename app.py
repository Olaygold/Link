from flask import Flask, request, redirect, render_template_string, session, g
import psycopg2
import psycopg2.extras
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "secret123")
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    if 'db' not in g:
        g.db = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db:
        db.close()

def init_db():
    db = get_db()
    cur = db.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS links (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='links'")
    columns = [row['column_name'] for row in cur.fetchall()]
    if 'views' not in columns:
        cur.execute("ALTER TABLE links ADD COLUMN views INTEGER DEFAULT 0")
    if 'clicks' not in columns:
        cur.execute("ALTER TABLE links ADD COLUMN clicks INTEGER DEFAULT 0")

    db.commit()
    cur.close()

with app.app_context():
    init_db()

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
    return render_template_string(public_html, links=links, admin=session.get('admin', False))

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
# ========== HTML ==============
# ===============================

login_html = '''
<!DOCTYPE html>
<html>
<head>
  <title>Admin Login</title>
  <style>
    body {
      background: linear-gradient(to right, #4b0082, #8a2be2);
      font-family: 'Segoe UI', sans-serif;
      color: white;
      text-align: center;
      padding-top: 100px;
    }
    .login-box {
      background: white;
      color: #333;
      padding: 30px;
      border-radius: 12px;
      width: 90%;
      max-width: 400px;
      margin: auto;
      box-shadow: 0 6px 12px rgba(0,0,0,0.2);
    }
    input {
      width: 90%;
      padding: 12px;
      margin: 10px 0;
      border: 1px solid #ccc;
      border-radius: 6px;
    }
    button {
      background: #6a0dad;
      color: white;
      border: none;
      padding: 12px 24px;
      border-radius: 30px;
      cursor: pointer;
      font-weight: bold;
    }
    button:hover {
      background: #4b0082;
    }
    .error { color: red; }
  </style>
</head>
<body>
  <div class="login-box">
    <h2>Admin Panel</h2>
    {% if error %}<p class="error">{{ error }}</p>{% endif %}
    <form method="post">
      <input name="username" placeholder="Username" required><br>
      <input name="password" type="password" placeholder="Password" required><br>
      <button type="submit">Login</button>
    </form>
  </div>
</body>
</html>
'''

dashboard_html = '''
<!DOCTYPE html>
<html>
<head>
  <title>Admin Dashboard</title>
  <style>
    body {
      font-family: 'Segoe UI', sans-serif;
      background: #f5f5fa;
      padding: 30px;
      color: #333;
    }
    h2 { color: #4b0082; }
    form { margin-bottom: 20px; }
    input {
      padding: 10px;
      border: 1px solid #ccc;
      border-radius: 6px;
      margin-right: 10px;
      width: 200px;
    }
    button {
      background: #6a0dad;
      color: white;
      padding: 10px 18px;
      border: none;
      border-radius: 30px;
      font-weight: bold;
      cursor: pointer;
    }
    button:hover { background: #4b0082; }
    a {
      color: red;
      text-decoration: none;
      margin-left: 10px;
    }
    hr { border: none; border-top: 1px solid #ccc; margin: 15px 0; }
    small { color: gray; }
  </style>
</head>
<body>
  <h2>Admin Dashboard</h2>
  <a href="/logout">🚪 Logout</a><br><br>
  <form method="post" action="/add">
    <input name="title" placeholder="Topic Title" required>
    <input name="url" placeholder="Link URL" required>
    <button type="submit">Add Topic</button>
  </form>
  <h3>Topics</h3>
  {% for link in links %}
    <form method="post" action="/edit/{{ link.id }}">
      <input name="title" value="{{ link.title }}" required>
      <input name="url" value="{{ link.url }}" required>
      <button type="submit">Update</button>
      <a href="/delete/{{ link.id }}" onclick="return confirm('Delete this topic?')">Delete</a><br>
      <small>Views: {{ link.views }} | Clicks: {{ link.clicks }}</small>
    </form>
    <hr>
  {% endfor %}
</body>
</html>
'''

public_html = '''
<!DOCTYPE html>
<html>
<head>
  <title>Join Our Money Update Circle 💸</title>
  <style>
    body {
      font-family: 'Segoe UI', sans-serif;
      margin: 0;
      padding: 0;
      background: linear-gradient(135deg, #4b0082, #8a2be2);
      color: white;
    }
    .container {
      max-width: 800px;
      margin: auto;
      padding: 30px 20px;
    }
    h2 {
      text-align: center;
      font-size: 30px;
      margin-bottom: 30px;
      animation: fadeIn 1.2s ease-in;
    }
    .topic {
      background: white;
      color: #333;
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 20px;
      box-shadow: 0 6px 12px rgba(0,0,0,0.15);
      transition: transform 0.2s;
    }
    .topic:hover {
      transform: scale(1.03);
    }
    .title {
      font-size: 20px;
      font-weight: bold;
      margin-bottom: 10px;
      color: #4b0082;
    }
    .btn {
      display: inline-block;
      padding: 10px 18px;
      border-radius: 30px;
      background: linear-gradient(to right, #6a0dad, #8a2be2);
      color: white;
      text-decoration: none;
      font-weight: bold;
      transition: background 0.3s ease;
    }
    .btn:hover { background: #4b0082; }
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(-20px); }
      to { opacity: 1; transform: translateY(0); }
    }
  </style>
</head>
<body>
  <div class="container">
    <h2>🚀 Join the Latest 💰 Money-Making Updates</h2>
    {% for link in links %}
      <div class="topic">
        <div class="title">{{ link.title }}</div>
        <a href="/click/{{ link.id }}" class="btn" target="_blank">👉 Tap to View & Join</a><br><br>
        {% if admin %}
          <small>Views: {{ link.views }} | Clicks: {{ link.clicks }}</small>
        {% endif %}
      </div>
    {% endfor %}
  </div>
</body>
</html>
'''
