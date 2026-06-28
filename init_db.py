import sqlite3
import os

DB_PATH = 'database.db'

def init_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create Users table
    cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')
    
    # Create Issues table
    cursor.execute('''
        CREATE TABLE issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tracking_code TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            impact_scale INTEGER,
            timeline TEXT,
            desired_support TEXT,
            status TEXT DEFAULT 'Pending',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create Notes table
    cursor.execute('''
        CREATE TABLE notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            issue_id INTEGER NOT NULL,
            counselor_id INTEGER NOT NULL,
            note_content TEXT NOT NULL,
            is_private BOOLEAN DEFAULT 1,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (issue_id) REFERENCES issues (id),
            FOREIGN KEY (counselor_id) REFERENCES users (id)
        )
    ''')
    
    # Insert mock users
    cursor.execute("INSERT INTO users (username, password, role) VALUES ('admin1', 'pass', 'admin')")
    cursor.execute("INSERT INTO users (username, password, role) VALUES ('counselor1', 'pass', 'counselor')")
    
    conn.commit()
    conn.close()
    print("Database initialized successfully.")

if __name__ == '__main__':
    init_db()
