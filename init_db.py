import sqlite3

conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

cursor.execute('DROP TABLE IF EXISTS private_messages')
cursor.execute('DROP TABLE IF EXISTS subscriptions')
cursor.execute('DROP TABLE IF EXISTS files')
cursor.execute('DROP TABLE IF EXISTS messages')
cursor.execute('DROP TABLE IF EXISTS topics')
cursor.execute('DROP TABLE IF EXISTS sections')
cursor.execute('DROP TABLE IF EXISTS users')


cursor.execute('''
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    full_name TEXT,
    role TEXT DEFAULT 'user',
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

cursor.execute('''
CREATE TABLE sections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT
)
''')


cursor.execute('''
CREATE TABLE topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT,
    section_id INTEGER,
    author_id INTEGER,
    status TEXT DEFAULT 'open',
    views INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (section_id) REFERENCES sections(id),
    FOREIGN KEY (author_id) REFERENCES users(id)
)
''')


cursor.execute('''
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    topic_id INTEGER,
    author_id INTEGER,
    is_edited INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (topic_id) REFERENCES topics(id),
    FOREIGN KEY (author_id) REFERENCES users(id)
)
''')


cursor.execute('''
CREATE TABLE files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    filepath TEXT NOT NULL,
    mime_type TEXT,
    size INTEGER,
    message_id INTEGER,
    FOREIGN KEY (message_id) REFERENCES messages(id)
)
''')


cursor.execute('''
CREATE TABLE subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    topic_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (topic_id) REFERENCES topics(id),
    UNIQUE(user_id, topic_id)
)
''')


cursor.execute('''
CREATE TABLE private_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_user_id INTEGER,
    to_user_id INTEGER,
    content TEXT,
    is_read INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (from_user_id) REFERENCES users(id),
    FOREIGN KEY (to_user_id) REFERENCES users(id)
)
''')

#Администратор (пароль: admin123)
cursor.execute('''
INSERT OR IGNORE INTO users (email, password, full_name, role)
VALUES ('admin@college.ru', '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918', 'Администратор', 'admin')
''')


sections_data = [
    ('Математика', 'Вопросы по алгебре, геометрии, математическому анализу'),
    ('История', 'История России и всемирная история'),
    ('Программирование', 'Python, Java, C++, веб-разработка'),
    ('Физика', 'Механика, термодинамика, оптика, квантовая физика'),
    ('Английский язык', 'Грамматика, лексика, подготовка к экзаменам'),
    ('Русский язык', 'Правила, сочинения, подготовка к ЕГЭ'),
    ('Химия', 'Органическая и неорганическая химия'),
    ('Биология', 'Анатомия, ботаника, зоология, генетика'),
]

for name, desc in sections_data:
    cursor.execute('INSERT OR IGNORE INTO sections (name, description) VALUES (?, ?)', (name, desc))

conn.commit()
conn.close()

print("База данных успешно создана!")
print(" Созданы таблицы: users, sections, topics, messages, files, subscriptions, private_messages")
print("Тестовый администратор: admin@college.ru / admin123")
print("Добавлены разделы: Математика, История, Программирование, Физика, Английский язык, Русский язык, Химия, Биология")