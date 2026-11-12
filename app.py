import html
import sqlite3

from flask import Flask, g, redirect, request, session

app = Flask(__name__)
app.secret_key = "super-secret-key-for-lab"
app.config["SESSION_COOKIE_HTTPONLY"] = False

DB_PATH = "lab.db"


def page(title, body):
    if session.get("username"):
        who = (
            f"Вы: {html.escape(session['username'])} "
            f'(<a href="/logout">выйти</a>)'
        )
    else:
        who = '<a href="/login">Войти</a>'

    return f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><title>{html.escape(title)}</title></head>
<body>
<nav>
  <a href="/">Главная</a> |
  <a href="/notes">Заметки</a> |
  <a href="/register">Регистрация</a> |
  {who}
</nav><hr>
{body}
</body></html>"""


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript(
        """
        DROP TABLE IF EXISTS users;
        DROP TABLE IF EXISTS notes;
        CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, password TEXT, role TEXT);
        CREATE TABLE notes (id INTEGER PRIMARY KEY, author TEXT, text TEXT);
        INSERT INTO users (username, password, role) VALUES
            ('admin', 'S3cr3t_Adm1n_Pass', 'admin'),
            ('alice', 'alice123', 'user'),
            ('bob',   'qwerty',   'user');
        """
    )
    db.commit()
    db.close()


@app.route("/")
def index():
    body = """
<h1>Мои Заметки</h1>
<p>Простой сервис для личных заметок: записывайте мысли, идеи и напоминания.</p>
<p>Перейдите в раздел <a href="/notes">Заметки</a>, чтобы оставить свою запись,
или <a href="/register">зарегистрируйтесь</a>, чтобы заметки сохранялись под вашим именем.</p>
"""
    return page("Мои Заметки", body)


@app.route("/login", methods=["GET", "POST"])
def login():
    error_html = ""
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        query = (
            "SELECT id, username, role FROM users "
            f"WHERE username = '{username}' AND password = '{password}'"
        )
        try:
            user = get_db().execute(query).fetchone()
        except sqlite3.Error as e:
            error_html = f'<p style="color:red">Ошибка БД: {html.escape(str(e))}</p>'
            user = None

        if user:
            session["username"] = user[1]
            session["role"] = user[2]
            return redirect("/")
        if not error_html:
            error_html = '<p style="color:red">Неверный логин или пароль</p>'

    body = f"""<h2>Вход</h2>
{error_html}
<form method="post">
  Логин: <input name="username"><br>
  Пароль: <input name="password" type="password"><br>
  <button>Войти</button>
</form>"""
    return page("Вход", body)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    error_html, success_html = "", ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not username or not password:
            error_html = '<p style="color:red">Укажите логин и пароль</p>'
        else:
            db = get_db()
            exists = db.execute(
                "SELECT 1 FROM users WHERE username = ?", (username,)
            ).fetchone()
            if exists:
                error_html = '<p style="color:red">Такой логин уже занят</p>'
            else:
                db.execute(
                    "INSERT INTO users (username, password, role) VALUES (?, ?, 'user')",
                    (username, password),
                )
                db.commit()
                success_html = (
                    '<p style="color:green">Готово! Теперь можно '
                    '<a href="/login">войти</a>.</p>'
                )

    body = f"""<h2>Регистрация</h2>
{error_html}
{success_html}
<form method="post">
  Логин: <input name="username"><br>
  Пароль: <input name="password" type="password"><br>
  <button>Зарегистрироваться</button>
</form>"""
    return page("Регистрация", body)


@app.route("/notes", methods=["GET", "POST"])
def notes():
    db = get_db()
    if request.method == "POST":
        text = request.form.get("text", "")
        author = session.get("username", "anonymous")
        db.execute("INSERT INTO notes (author, text) VALUES (?, ?)", (author, text))
        db.commit()
        return redirect("/notes")

    rows = db.execute("SELECT author, text FROM notes ORDER BY id").fetchall()
    notes_html = ""
    for author, text in rows:
        notes_html += (
            f'<div class="c"><b>{html.escape(author)}</b>: {text}</div>\n'
        )

    body = f"""<h2>Заметки</h2>
<form method="post">
  <textarea name="text" rows="3" cols="40"></textarea><br>
  <button>Сохранить</button>
</form>
{notes_html}"""
    return page("Заметки", body)


if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=False)
