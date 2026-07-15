import os
import random
import datetime
import pytz
from flask import Flask, render_template, request, redirect, url_for, jsonify
import mysql.connector
from mysql.connector import pooling
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
app.secret_key = os.urandom(24)

db_config = {
    "host": "localhost",
    "user": "root",
    "password": "Rootsed@2010",
    "database": "school_substitution"
}
db_pool = pooling.MySQLConnectionPool(pool_name="mypool", pool_size=15, **db_config)
IST = pytz.timezone('Asia/Kolkata')

def get_db_connection():
    return db_pool.get_connection()

def get_current_weekday():
    now = datetime.datetime.now(IST)
    day = now.strftime("%A").lower()
    return day if day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'] else 'monday'

def seed_demo_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM faculty")
    if cursor.fetchone()[0] == 0:
        demo_teachers = [
            ("Amit Sharma", "Senior"), ("Priya Patel", "Senior"), ("Vikram Singh", "Senior"), 
            ("Neha Gupta", "Senior"), ("Sanjay Dutt", "Senior"), ("Anjali Desai", "Middle"), 
            ("Rajesh Kumar", "Middle"), ("Kavita Rao", "Middle"), ("Arjun Malhotra", "Middle"), 
            ("Sunita Verma", "Middle"), ("Deepak Joshi", "Middle"), ("Meera Nair", "Middle"), 
            ("Rohan Das", "Primary"), ("Swati Mishra", "Primary"), ("Aman Verma", "Primary"), 
            ("Pooja Reddy", "Primary"), ("Karan Johar", "Primary"), ("Divya Teja", "Primary"), 
            ("Vijay Yadav", "Primary"), ("Sapna Choudhary", "Primary")
        ]
        subjects = ["English", "Science", "Maths", "History", "Geography", None, None]
        for name, wing in demo_teachers:
            cursor.execute("INSERT INTO faculty (name, wing, total_absences, total_substitutions) VALUES (%s, %s, %s, %s)", 
                           (name, wing, random.randint(0,4), random.randint(0,6)))
            fid = cursor.lastrowid
            days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
            sched_vals = [fid]
            for d in days:
                for p in range(1, 8):
                    sched_vals.append(random.choice(subjects))
            
            query = f"INSERT INTO timetable (faculty_id, {', '.join([f'{d}_p{p}' for d in days for p in range(1,8)])}) VALUES ({', '.join(['%s']*36)})"
            cursor.execute(query, tuple(sched_vals))
        conn.commit()
    cursor.close()
    conn.close()

def calculate_substitute_recommendations(absent_teacher, period, weekday):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT f.*, da.status as attendance_status FROM faculty f LEFT JOIN daily_attendance da ON f.id = da.faculty_id")
    all_teachers = cursor.fetchall()
    
    period_col = f"{weekday}_p{period}"
    cursor.execute(f"SELECT faculty_id, {period_col} FROM timetable")
    # A teacher is busy if the column contains a string value (subject name)
    timetable_map = {row['faculty_id']: row[period_col] for row in cursor.fetchall()}
    
    cursor.execute("SELECT substitute_faculty_id FROM live_substitutions WHERE period = %s AND substitute_faculty_id IS NOT NULL", (period,))
    busy_subs = {row['substitute_faculty_id'] for row in cursor.fetchall()}
    cursor.close()
    conn.close()
    
    eligible_pool = []
    absent_wing = absent_teacher['wing']
    for t in all_teachers:
        t_id = t['id']
        # Check if teacher is absent, has an active class name assigned, or is already covering a substitution
        if t_id == absent_teacher['id'] or t.get('attendance_status') == 'Absent':
            continue
        if timetable_map.get(t_id) is not None and timetable_map.get(t_id) != "" and timetable_map.get(t_id) != "0":
            continue
        if t_id in busy_subs:
            continue
        if absent_wing in ['Senior', 'Middle'] and t['wing'] == 'Primary':
            continue
        eligible_pool.append(t)
        
    eligible_pool.sort(key=lambda x: (0 if x['wing'] == absent_wing else 1, -x['total_absences'], x['total_substitutions']))
    return eligible_pool

# --- APP WEB OPERATIONS ---
@app.route('/')
def public_dashboard():
    weekday = get_current_weekday()
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT f.id, f.name, f.wing, COALESCE(da.status, 'Present') as current_status FROM faculty f LEFT JOIN daily_attendance da ON f.id = da.faculty_id")
    roster = cursor.fetchall()
    cursor.execute("""
        SELECT ls.period, f1.name as absent_teacher, f2.name as substitute_teacher
        FROM live_substitutions ls JOIN faculty f1 ON ls.absent_faculty_id = f1.id
        LEFT JOIN faculty f2 ON ls.substitute_faculty_id = f2.id ORDER BY ls.period
    """)
    live_subs = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('dashboard.html', roster=roster, live_subs=live_subs, weekday=weekday.capitalize())

@app.route('/admin')
def admin_panel():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT f.*, COALESCE(da.status, 'Present') as current_status FROM faculty f LEFT JOIN daily_attendance da ON f.id = da.faculty_id")
    faculty_list = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin.html', faculty_list=faculty_list)

@app.route('/admin/teacher/add', methods=['POST'])
def add_teacher():
    name, wing = request.form.get('name'), request.form.get('wing')
    if name and wing:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO faculty (name, wing) VALUES (%s, %s)", (name, wing))
        fid = cursor.lastrowid
        cursor.execute("INSERT INTO timetable (faculty_id) VALUES (%s)", (fid,))
        conn.commit()
        cursor.close()
        conn.close()
    return redirect(url_for('admin_panel'))

@app.route('/admin/teacher/update/<int:faculty_id>', methods=['POST'])
def update_teacher(faculty_id):
    name, wing = request.form.get('name'), request.form.get('wing')
    if name and wing:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE faculty SET name = %s, wing = %s WHERE id = %s", (name, wing, faculty_id))
        conn.commit()
        cursor.close()
        conn.close()
    return redirect(url_for('admin_panel'))

@app.route('/admin/teacher/delete/<int:faculty_id>', methods=['POST'])
def delete_teacher(faculty_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM faculty WHERE id = %s", (faculty_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('admin_panel'))

@app.route('/admin/timetable/update/<int:faculty_id>', methods=['POST'])
def update_timetable(faculty_id):
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
    update_parts, params = [], []
    for day in days:
        for period in range(1, 8):
            field_name = f"{day}_p{period}"
            val = request.form.get(field_name, "").strip()
            update_parts.append(f"{field_name} = %s")
            # Save empty strings as None/NULL to indicate the period is open
            params.append(val if val != "" else None)
    params.append(faculty_id)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE timetable SET {', '.join(update_parts)} WHERE faculty_id = %s", tuple(params))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('admin_panel'))

@app.route('/api/timetable/<int:faculty_id>')
def get_teacher_timetable(faculty_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM timetable WHERE faculty_id = %s", (faculty_id,))
    res = cursor.fetchone()
    cursor.close()
    conn.close()
    return jsonify(res) if res else (jsonify({"error": "Not Found"}), 404)

@app.route('/admin/toggle-status/<int:faculty_id>', methods=['POST'])
def toggle_status(faculty_id):
    new_status = request.form.get('status')
    weekday = get_current_weekday()
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("INSERT INTO daily_attendance (faculty_id, status) VALUES (%s, %s) ON DUPLICATE KEY UPDATE status = %s", (faculty_id, new_status, new_status))
    if new_status == 'Absent':
        period_cols = [f"{weekday}_p{i}" for i in range(1, 8)]
        cursor.execute(f"SELECT {', '.join(period_cols)} FROM timetable WHERE faculty_id = %s", (faculty_id,))
        schedule = cursor.fetchone()
        if schedule:
            for i in range(1, 8):
                # If there is an active class string assigned, add it to required substitutions
                if schedule[f"{weekday}_p{i}"] is not None and schedule[f"{weekday}_p{i}"] != "":
                    cursor.execute("INSERT IGNORE INTO live_substitutions (absent_faculty_id, period) VALUES (%s, %s)", (faculty_id, i))
    else:
        cursor.execute("DELETE FROM live_substitutions WHERE absent_faculty_id = %s", (faculty_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('suggest_substitutes', faculty_id=faculty_id)) if new_status == 'Absent' else redirect(url_for('admin_panel'))

@app.route('/admin/suggest-substitutes/<int:faculty_id>')
def suggest_substitutes(faculty_id):
    weekday = get_current_weekday()
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM faculty WHERE id = %s", (faculty_id,))
    absent_teacher = cursor.fetchone()
    cursor.execute("SELECT * FROM live_substitutions WHERE absent_faculty_id = %s ORDER BY period", (faculty_id,))
    needed_periods = cursor.fetchall()
    matrix = {}
    for entry in needed_periods:
        p = entry['period']
        matrix[p] = {
            'assigned_id': entry['substitute_faculty_id'],
            'options': calculate_substitute_recommendations(absent_teacher, p, weekday)
        }
    cursor.close()
    conn.close()
    return render_template('suggest.html', absent_teacher=absent_teacher, matrix=matrix)

@app.route('/admin/assign-substitute', methods=['POST'])
def assign_substitute():
    absent_id, period = request.form.get('absent_id'), request.form.get('period')
    sub_id = request.form.get('substitute_id') or None
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE live_substitutions SET substitute_faculty_id = %s WHERE absent_faculty_id = %s AND period = %s", (sub_id, absent_id, period))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('suggest_substitutes', faculty_id=absent_id))

if __name__ == '__main__':
    seed_demo_data()
    app.run(host='0.0.0.0', port=5000, debug=True)
