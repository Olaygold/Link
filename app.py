from flask import Flask, request, redirect, render_template_string, session, g
import sqlite3
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "secret123")

# Use relative path so SQLite works in Render
DATABASE = os.path.join(os.path.dirname(__file__), 'links.db')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

def init_db():
    with app.app_context():
        db = get_db()
        db.execute('''CREATE TABLE IF NOT EXISTS links (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        url TEXT NOT NULL,
                        views INTEGER DEFAULT 0,
                        clicks INTEGER DEFAULT 0)''')
        db.commit()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/')
def home():
    db = get_db()
    links = db.execute("SELECT * FROM links").fetchall()
    db.execute("UPDATE links SET views = views + 1")
    db.commit()
    return render_template_string(public_html, links=links)

@app.route('/click/<int:link_id>')
def click(link_id):
    db = get_db()
    db.execute("UPDATE links SET clicks = clicks + 1 WHERE id = ?", (link_id,))
    url = db.execute("SELECT url FROM links WHERE id = ?", (link_id,)).fetchone()['url']
    db.commit()
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
    links = db.execute("SELECT * FROM links").fetchall()
    return render_template_string(dashboard_html, links=links)

@app.route('/add', methods=['POST'])
def add():
    if not session.get('admin'):
        return redirect('/login')
    title = request.form['title']
    url = request.form['url']
    db = get_db()
    db.execute("INSERT INTO links (title, url) VALUES (?, ?)", (title, url))
    db.commit()
    return redirect('/dashboard')

@app.route('/delete/<int:link_id>')
def delete(link_id):
    if not session.get('admin'):
        return redirect('/login')
    db = get_db()
    db.execute("DELETE FROM links WHERE id = ?", (link_id,))
    db.commit()
    return redirect('/dashboard')

@app.route('/edit/<int:link_id>', methods=['POST'])
def edit(link_id):
    if not session.get('admin'):
        return redirect('/login')
    title = request.form['title']
    url = request.form['url']
    db = get_db()
    db.execute("UPDATE links SET title = ?, url = ? WHERE id = ?", (title, url, link_id))
    db.commit()
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
      <small>Views: {{ link.views }}, Clicks: {{ link.clicks }}</small>
    </div>
  {% endfor %}
</body>
</html>
'''

# Run it
@app.before_first_request
def setup():
    init_db()
    
