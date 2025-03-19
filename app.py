from flask import Flask, render_template, request, jsonify, session
import sqlite3
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Change this to a secure secret key

def init_db():
    try:
        conn = sqlite3.connect('university.db')
        c = conn.cursor()
        
        # Create tables
        c.execute('''CREATE TABLE IF NOT EXISTS students
                     (id TEXT PRIMARY KEY, name TEXT NOT NULL, department TEXT, year INTEGER,
                      gpa REAL, classroom TEXT, faculty_name TEXT)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS class_routine
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT,
                      day TEXT, time TEXT, subject TEXT, room TEXT,
                      FOREIGN KEY (student_id) REFERENCES students (id))''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS messages
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT NOT NULL,
                      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                      is_bot BOOLEAN DEFAULT 0,
                      student_id TEXT,
                      FOREIGN KEY (student_id) REFERENCES students (id))''')
        
        # Add sample data if no students exist
        c.execute('SELECT COUNT(*) FROM students')
        if c.fetchone()[0] == 0:
            # Add sample student
            c.execute('''INSERT INTO students (id, name, department, year, gpa, classroom, faculty_name)
                         VALUES (?, ?, ?, ?, ?, ?, ?)''',
                     ('2024001', 'John Doe', 'Computer Science', 1, 3.8, 'Room 301', 'Dr. Smith'))
            
            # Add sample class routine
            routine_data = [
                ('2024001', 'Monday', '09:00-10:30', 'Programming', 'Room 301'),
                ('2024001', 'Monday', '11:00-12:30', 'Mathematics', 'Room 302'),
                ('2024001', 'Tuesday', '09:00-10:30', 'Physics', 'Room 303'),
                ('2024001', 'Tuesday', '11:00-12:30', 'English', 'Room 304'),
                ('2024001', 'Wednesday', '09:00-10:30', 'Programming', 'Room 301'),
                ('2024001', 'Wednesday', '11:00-12:30', 'Mathematics', 'Room 302'),
                ('2024001', 'Thursday', '09:00-10:30', 'Physics', 'Room 303'),
                ('2024001', 'Thursday', '11:00-12:30', 'English', 'Room 304'),
                ('2024001', 'Friday', '09:00-10:30', 'Programming', 'Room 301'),
                ('2024001', 'Friday', '11:00-12:30', 'Mathematics', 'Room 302')
            ]
            c.executemany('''INSERT INTO class_routine (student_id, day, time, subject, room)
                            VALUES (?, ?, ?, ?, ?)''', routine_data)
        
        conn.commit()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise
    finally:
        conn.close()

# Initialize database
init_db()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    try:
        student_id = request.form.get('student_id')
        logger.debug(f"Login attempt for student ID: {student_id}")
        
        conn = sqlite3.connect('university.db')
        c = conn.cursor()
        c.execute('SELECT name FROM students WHERE id = ?', (student_id,))
        result = c.fetchone()
        conn.close()
        
        if result:
            session['student_id'] = student_id
            logger.info(f"Successful login for student: {result[0]}")
            return jsonify({'success': True, 'name': result[0]})
        logger.warning(f"Failed login attempt for student ID: {student_id}")
        return jsonify({'success': False, 'message': 'Invalid student ID'})
    except Exception as e:
        logger.error(f"Error during login: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred during login'})

@app.route('/chat', methods=['POST'])
def chat():
    try:
        if 'student_id' not in session:
            logger.warning("Chat attempt without login")
            return jsonify({'success': False, 'message': 'Please login first'})
        
        message_content = request.form.get('message')
        if not message_content:
            logger.warning("Empty message received")
            return jsonify({'success': False, 'message': 'Message cannot be empty'})
            
        student_id = session['student_id']
        logger.debug(f"Received message from student {student_id}: {message_content}")
        
        conn = sqlite3.connect('university.db')
        c = conn.cursor()
        
        try:
            # Save user message
            c.execute('INSERT INTO messages (content, student_id, is_bot) VALUES (?, ?, ?)',
                     (message_content, student_id, False))
            
            # Get student data
            c.execute('''SELECT name, department, year, gpa, classroom, faculty_name 
                         FROM students WHERE id = ?''', (student_id,))
            student = c.fetchone()
            
            if not student:
                logger.error(f"Student data not found for ID: {student_id}")
                return jsonify({'success': False, 'message': 'Student data not found'})
            
            # Generate bot response
            bot_response = generate_response(message_content, student, c)
            logger.debug(f"Generated bot response: {bot_response}")
            
            # Save bot response
            c.execute('INSERT INTO messages (content, student_id, is_bot) VALUES (?, ?, ?)',
                     (bot_response, student_id, True))
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'response': bot_response
            })
            
        except sqlite3.Error as e:
            logger.error(f"Database error: {str(e)}")
            conn.rollback()
            return jsonify({'success': False, 'message': 'Database error occurred'})
            
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred while processing your message'})
    finally:
        if 'conn' in locals():
            conn.close()

def generate_response(message, student, cursor):
    try:
        # Simple response generation based on student data
        message = message.lower().strip()
        name, department, year, gpa, classroom, faculty_name = student
        
        if 'name' in message:
            return f"Your name is {name}"
        elif 'department' in message:
            return f"You are in the {department} department"
        elif 'year' in message:
            return f"You are in year {year}"
        elif 'id' in message:
            return f"Your student ID is {session['student_id']}"
        elif 'gpa' in message:
            return f"Your current GPA is {gpa}"
        elif 'classroom' in message:
            return f"Your classroom is {classroom}"
        elif 'faculty' in message:
            return f"Your faculty advisor is {faculty_name}"
        elif 'routine' in message or 'schedule' in message:
            cursor.execute('''SELECT day, time, subject, room 
                             FROM class_routine 
                             WHERE student_id = ? 
                             ORDER BY 
                                 CASE day 
                                     WHEN 'Monday' THEN 1
                                     WHEN 'Tuesday' THEN 2
                                     WHEN 'Wednesday' THEN 3
                                     WHEN 'Thursday' THEN 4
                                     WHEN 'Friday' THEN 5
                                     ELSE 6
                                 END, time''', (session['student_id'],))
            routine = cursor.fetchall()
            
            if not routine:
                return "You don't have any classes scheduled."
            
            response = "Here's your class routine:\n\n"
            current_day = None
            for day, time, subject, room in routine:
                if day != current_day:
                    if current_day is not None:
                        response += "\n"
                    response += f"{day}:\n"
                    current_day = day
                response += f"  • {time} - {subject} ({room})\n"
            return response.strip()
        else:
            return "I can help you with information about your name, department, year, student ID, GPA, classroom, faculty advisor, and class routine. What would you like to know?"
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}")
        return "I apologize, but I encountered an error while processing your request. Please try again."

@app.route('/get_messages')
def get_messages():
    try:
        if 'student_id' not in session:
            logger.warning("Get messages attempt without login")
            return jsonify({'success': False, 'message': 'Please login first'})
        
        conn = sqlite3.connect('university.db')
        c = conn.cursor()
        c.execute('SELECT content, is_bot FROM messages WHERE student_id = ? ORDER BY timestamp',
                 (session['student_id'],))
        messages = [{'content': msg[0], 'is_bot': bool(msg[1])} for msg in c.fetchall()]
        conn.close()
        
        return jsonify({
            'success': True,
            'messages': messages
        })
    except Exception as e:
        logger.error(f"Error getting messages: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred while fetching messages'})

if __name__ == '__main__':
    app.run(debug=True) 