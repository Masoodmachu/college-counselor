from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
import sqlite3

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_demo'

import init_db as db_init

if not os.path.exists('database.db'):
    print("Database not found. Initializing new database...")
    db_init.init_db()
    
    # Create the default admin user
    conn = sqlite3.connect('database.db')
    conn.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES ('admin', 'admin', 'admin')")
    conn.commit()
    conn.close()
    print("Database initialized and admin user created.")

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

import uuid

@app.route('/')
def index():
    return render_template('public.html')

@app.route('/counselor-login')
def counselor_login():
    if 'user_id' in session:
        if session['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif session['role'] == 'counselor':
            return redirect(url_for('counselor_dashboard'))
    return render_template('index.html')

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
    conn.close()
    
    if user:
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        return jsonify({'success': True, 'role': user['role']})
    return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/register')
def register_page():
    # In a real app, you would restrict this to an admin.
    # For now, it's accessible to allow creating accounts.
    return render_template('register.html')

@app.route('/api/register', methods=['POST'])
def register_user():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    role = data.get('role')
    
    if not username or not password or role not in ['student', 'counselor']:
        return jsonify({'success': False, 'message': 'Invalid input'}), 400
        
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', (username, password, role))
        conn.commit()
        success = True
        message = 'Success'
    except sqlite3.IntegrityError:
        success = False
        message = 'Username already exists'
    conn.close()
    
    return jsonify({'success': success, 'message': message})

@app.route('/api/issues', methods=['GET', 'POST'])
def handle_issues():
    conn = get_db_connection()
    
    if request.method == 'POST':
        data = request.get_json()
        title = data.get('title')
        description = data.get('description')
        impact_scale = data.get('impact_scale')
        timeline = data.get('timeline')
        desired_support = data.get('desired_support')
        
        tracking_code = 'TKT-' + str(uuid.uuid4())[:8].upper()
        
        cursor = conn.execute('INSERT INTO issues (tracking_code, title, description, impact_scale, timeline, desired_support) VALUES (?, ?, ?, ?, ?, ?)',
                              (tracking_code, title, description, impact_scale, timeline, desired_support))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'tracking_code': tracking_code})
        
    else: # GET (Counselor only now)
        if 'user_id' not in session or session['role'] != 'counselor':
            conn.close()
            return jsonify({'error': 'Unauthorized'}), 401
            
        issues = conn.execute('SELECT * FROM issues ORDER BY timestamp DESC').fetchall()
        conn.close()
        return jsonify([dict(ix) for ix in issues])

@app.route('/api/issues/<tracking_code>', methods=['GET'])
def get_issue_by_code(tracking_code):
    conn = get_db_connection()
    issue = conn.execute('SELECT * FROM issues WHERE tracking_code = ?', (tracking_code,)).fetchone()
    if not issue:
        conn.close()
        return jsonify({'error': 'Not found'}), 404
        
    issue_dict = dict(issue)
    replies = conn.execute('''
        SELECT notes.note_content, notes.timestamp, users.username as counselor_username 
        FROM notes 
        JOIN users ON notes.counselor_id = users.id 
        WHERE issue_id = ? AND is_private = 0 
        ORDER BY timestamp ASC
    ''', (issue['id'],)).fetchall()
    issue_dict['replies'] = [dict(rx) for rx in replies]
    
    conn.close()
    return jsonify(issue_dict)

@app.route('/api/issues/<int:issue_id>/seen', methods=['POST'])
def mark_seen(issue_id):
    if 'user_id' not in session or session['role'] != 'counselor':
        return jsonify({'error': 'Unauthorized'}), 401
    conn = get_db_connection()
    conn.execute("UPDATE issues SET status = 'Seen' WHERE id = ? AND status = 'Pending'", (issue_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/counselor')
def counselor_dashboard():
    if 'user_id' not in session or session['role'] != 'counselor':
        return redirect(url_for('counselor_login'))
    return render_template('counselor.html', username=session['username'])

@app.route('/admin')
def admin_dashboard():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('counselor_login'))
    return render_template('admin.html', username=session['username'])

@app.route('/api/admin/counselors', methods=['GET', 'POST'])
def manage_counselors():
    if 'user_id' not in session or session['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
        
    conn = get_db_connection()
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        try:
            conn.execute("INSERT INTO users (username, password, role) VALUES (?, ?, 'counselor')", (username, password))
            conn.commit()
            success = True
        except sqlite3.IntegrityError:
            success = False
        conn.close()
        return jsonify({'success': success})
    else:
        counselors = conn.execute("SELECT id, username FROM users WHERE role = 'counselor'").fetchall()
        conn.close()
        return jsonify([dict(c) for c in counselors])

@app.route('/api/admin/counselors/<int:user_id>', methods=['DELETE'])
def delete_counselor(user_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = get_db_connection()
    conn.execute("DELETE FROM users WHERE id = ? AND role = 'counselor'", (user_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/admin/counselors/<int:user_id>/activity', methods=['GET'])
def get_counselor_activity(user_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = get_db_connection()
    counselor = conn.execute("SELECT username FROM users WHERE id = ? AND role = 'counselor'", (user_id,)).fetchone()
    if not counselor:
        conn.close()
        return jsonify({'error': 'Counselor not found'}), 404
        
    activities = conn.execute('''
        SELECT notes.note_content, notes.is_private, notes.timestamp, issues.tracking_code, issues.title 
        FROM notes 
        JOIN issues ON notes.issue_id = issues.id 
        WHERE notes.counselor_id = ? 
        ORDER BY notes.timestamp DESC
    ''', (user_id,)).fetchall()
    conn.close()
    
    return jsonify({
        'counselor_username': counselor['username'],
        'activities': [dict(a) for a in activities]
    })

@app.route('/api/issues/<int:issue_id>/notes', methods=['GET', 'POST'])
def handle_notes(issue_id):
    if 'user_id' not in session or session['role'] != 'counselor':
        return jsonify({'error': 'Unauthorized'}), 401
        
    conn = get_db_connection()
    
    if request.method == 'POST':
        data = request.get_json()
        note_content = data.get('note_content')
        is_private = data.get('is_private', True)
        conn.execute('INSERT INTO notes (issue_id, counselor_id, note_content, is_private) VALUES (?, ?, ?, ?)',
                     (issue_id, session['user_id'], note_content, is_private))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
        
    else: # GET
        notes = conn.execute('''
            SELECT notes.*, users.username as counselor_username 
            FROM notes 
            JOIN users ON notes.counselor_id = users.id 
            WHERE issue_id = ? 
            ORDER BY timestamp ASC
        ''', (issue_id,)).fetchall()
        conn.close()
        return jsonify([dict(nx) for nx in notes])

if __name__ == '__main__':
    app.run(debug=True, port=5000)
