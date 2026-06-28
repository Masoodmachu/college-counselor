import sqlite3
conn = sqlite3.connect('database.db')
conn.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES ('admin', 'admin', 'admin')")
conn.execute("UPDATE users SET role='admin' WHERE username='admin' OR username LIKE '%admin%'")
conn.commit()
conn.close()
