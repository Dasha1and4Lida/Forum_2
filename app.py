from flask import Flask, render_template, request, redirect, session, flash, send_file
import sqlite3
import hashlib
import io
from functools import wraps

app = Flask(__name__)
app.secret_key = 'секретный-ключ-форума-2026'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите в систему')
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@app.route('/section/<int:section_id>')
def index(section_id=None):
    query = request.args.get('q', '')
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    
    sections = cursor.execute("SELECT * FROM sections").fetchall()
    
    if query:
        topics = cursor.execute("""
            SELECT t.*, 
                   u.full_name as author_name, 
                   s.name as section_name,
                   datetime(t.created_at, '+3 hours') as local_created_at
            FROM topics t
            JOIN users u ON t.author_id = u.id
            JOIN sections s ON t.section_id = s.id
            WHERE t.title LIKE ? OR t.content LIKE ?
            ORDER BY t.created_at DESC
        """, (f'%{query}%', f'%{query}%')).fetchall()
    else:
        if section_id:
            topics = cursor.execute("""
                SELECT t.*, 
                       u.full_name as author_name, 
                       s.name as section_name,
                       datetime(t.created_at, '+3 hours') as local_created_at
                FROM topics t
                JOIN users u ON t.author_id = u.id
                JOIN sections s ON t.section_id = s.id
                WHERE t.section_id = ?
                ORDER BY t.created_at DESC
            """, (section_id,)).fetchall()
        else:
            topics = cursor.execute("""
                SELECT t.*, 
                       u.full_name as author_name, 
                       s.name as section_name,
                       datetime(t.created_at, '+3 hours') as local_created_at
                FROM topics t
                JOIN users u ON t.author_id = u.id
                JOIN sections s ON t.section_id = s.id
                ORDER BY t.created_at DESC
            """).fetchall()
    
    conn.close()
    return render_template('index.html', sections=sections, topics=topics, query=query, current_section=section_id)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = hash_password(request.form['password'])
        full_name = request.form['full_name']
        conn = sqlite3.connect('db.sqlite3')
        try:
            conn.execute("INSERT INTO users (email, password, full_name) VALUES (?, ?, ?)",
                        (email, password, full_name))
            conn.commit()
            flash('Регистрация успешна!')
            return redirect('/login')
        except sqlite3.IntegrityError:
            flash('Email уже существует')
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = hash_password(request.form['password'])
        conn = sqlite3.connect('db.sqlite3')
        user = conn.execute("SELECT * FROM users WHERE email = ? AND password = ? AND is_active = 1",
                           (email, password)).fetchone()
        conn.close()
        if user:
            session['user_id'] = user[0]
            session['user_name'] = user[3]
            session['user_role'] = user[4]
            flash(f'Добро пожаловать, {user[3]}!')
            return redirect('/')
        else:
            flash('Неверный email или пароль')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из системы')
    return redirect('/')

@app.route('/create_topic', methods=['POST'])
@login_required
def create_topic():
    title = request.form['title']
    content = request.form['content']
    section_id = request.form['section_id']
    author_id = session['user_id']
    
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO topics (title, content, section_id, author_id)
        VALUES (?, ?, ?, ?)
    """, (title, content, section_id, author_id))
    
    topic_id = cursor.lastrowid
    
    files = request.files.getlist('files')
    for file in files:
        if file and file.filename:
            file_content = file.read()
            cursor.execute("""
                INSERT INTO files (filename, content, mime_type, size, message_id)
                VALUES (?, ?, ?, ?, ?)
            """, (file.filename, file_content, file.content_type, len(file_content), None))
    
    conn.commit()
    conn.close()
    
    flash('Тема создана!')
    return redirect('/')

@app.route('/topic/<int:topic_id>')
def view_topic(topic_id):
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    cursor.execute("UPDATE topics SET views = views + 1 WHERE id = ?", (topic_id,))
    
    topic = cursor.execute("""
        SELECT t.*, 
               u.full_name as author_name, 
               s.name as section_name,
               datetime(t.created_at, '+3 hours') as local_created_at
        FROM topics t
        JOIN users u ON t.author_id = u.id
        JOIN sections s ON t.section_id = s.id
        WHERE t.id = ?
    """, (topic_id,)).fetchone()
    
    messages = cursor.execute("""
        SELECT m.*, 
               u.full_name as author_name,
               datetime(m.created_at, '+3 hours') as local_created_at
        FROM messages m
        JOIN users u ON m.author_id = u.id
        WHERE m.topic_id = ?
        ORDER BY m.created_at ASC
    """, (topic_id,)).fetchall()
    
    messages_with_files = []
    for msg in messages:
        files = cursor.execute("SELECT id, filename, size FROM files WHERE message_id = ?", (msg[0],)).fetchall()
        messages_with_files.append(list(msg) + [files])
    
    conn.commit()
    conn.close()
    return render_template('topic.html', topic=topic, messages=messages_with_files)

@app.route('/add_message/<int:topic_id>', methods=['POST'])
@login_required
def add_message(topic_id):
    content = request.form['content']
    author_id = session['user_id']
    
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO messages (content, topic_id, author_id)
        VALUES (?, ?, ?)
    """, (content, topic_id, author_id))
    
    message_id = cursor.lastrowid
    
    files = request.files.getlist('files')
    for file in files:
        if file and file.filename:
            file_content = file.read()
            cursor.execute("""
                INSERT INTO files (filename, content, mime_type, size, message_id)
                VALUES (?, ?, ?, ?, ?)
            """, (file.filename, file_content, file.content_type, len(file_content), message_id))
    
    conn.commit()
    conn.close()
    
    flash('Ответ добавлен!')
    return redirect(f'/topic/{topic_id}')

@app.route('/download/<int:file_id>')
def download_file(file_id):
    conn = sqlite3.connect('db.sqlite3')
    file_data = conn.execute("SELECT filename, content, mime_type FROM files WHERE id = ?", (file_id,)).fetchone()
    conn.close()
    
    if file_data:
        return send_file(
            io.BytesIO(file_data[1]),
            as_attachment=True,
            download_name=file_data[0],
            mimetype=file_data[2]
        )
    
    flash('Файл не найден')
    return redirect('/')
    
@app.route('/edit_message/<int:message_id>', methods=['POST'])
@login_required
def edit_message(message_id):
    new_content = request.form['content']
    
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    
    message = cursor.execute("""
        SELECT topic_id FROM messages 
        WHERE id = ? AND author_id = ?
    """, (message_id, session['user_id'])).fetchone()
    
    if not message:
        flash('Сообщение не найдено или у вас нет прав на его редактирование')
        return redirect('/')
    
    cursor.execute("""
        UPDATE messages 
        SET content = ?, is_edited = 1, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (new_content, message_id))
    conn.commit()
    conn.close()
    
    flash('Сообщение отредактировано')
    return redirect(f'/topic/{message[0]}')

@app.route('/delete_message/<int:message_id>')
@login_required
def delete_message(message_id):
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    
    message = cursor.execute("""
        SELECT topic_id FROM messages 
        WHERE id = ? AND author_id = ?
    """, (message_id, session['user_id'])).fetchone()
    
    if not message:
        flash('Сообщение не найдено или у вас нет прав на его удаление')
        return redirect('/')
    
    cursor.execute("DELETE FROM messages WHERE id = ?", (message_id,))
    conn.commit()
    conn.close()
    
    flash('Сообщение удалено')
    return redirect(f'/topic/{message[0]}')

@app.route('/chat')
@login_required
def chat_list():
    conn = sqlite3.connect('db.sqlite3')
    users = conn.execute("SELECT id, full_name FROM users WHERE id != ?", (session['user_id'],)).fetchall()
    conn.close()
    return render_template('chat.html', users=users)

@app.route('/chat/<int:user_id>')
@login_required
def chat_with(user_id):
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    
    other = cursor.execute("SELECT id, full_name FROM users WHERE id = ?", (user_id,)).fetchone()
    cursor.execute("UPDATE private_messages SET is_read = 1 WHERE to_user_id = ? AND from_user_id = ?", (session['user_id'], user_id))
    messages = cursor.execute("""
        SELECT pm.*, u.full_name 
        FROM private_messages pm
        JOIN users u ON pm.from_user_id = u.id
        WHERE (from_user_id = ? AND to_user_id = ?) OR (from_user_id = ? AND to_user_id = ?)
        ORDER BY created_at ASC
    """, (session['user_id'], user_id, user_id, session['user_id'])).fetchall()
    conn.commit()
    conn.close()
    return render_template('chat_window.html', other=other, messages=messages)

@app.route('/send_message/<int:user_id>', methods=['POST'])
@login_required
def send_message(user_id):
    content = request.form['content']
    if content.strip():
        conn = sqlite3.connect('db.sqlite3')
        conn.execute("INSERT INTO private_messages (from_user_id, to_user_id, content) VALUES (?, ?, ?)", 
                     (session['user_id'], user_id, content))
        conn.commit()
        conn.close()
    return redirect(f'/chat/{user_id}')

if __name__ == '__main__':
    app.run(debug=True)
