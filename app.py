
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///health_monitoring.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    height = db.Column(db.Float, nullable=False)
    weight = db.Column(db.Float, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    health_records = db.relationship('HealthRecord', backref='user', lazy=True)
    exercise_logs = db.relationship('ExerciseLog', backref='user', lazy=True)
    water_logs = db.relationship('WaterLog', backref='user', lazy=True)
    sleep_logs = db.relationship('SleepLog', backref='user', lazy=True)
    mood_logs = db.relationship('MoodLog', backref='user', lazy=True)
    goals = db.relationship('Goal', backref='user', lazy=True)

class HealthRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    bmi = db.Column(db.Float, nullable=False)
    temperature = db.Column(db.Float)
    health_rating = db.Column(db.Integer)
    calories_consumed = db.Column(db.Float)
    calories_needed = db.Column(db.Float)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)

class ExerciseLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    exercise_type = db.Column(db.String(100), nullable=False)
    duration = db.Column(db.Integer, nullable=False)  # in minutes
    intensity = db.Column(db.String(20), nullable=False)
    calories_burned = db.Column(db.Float)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)

class WaterLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)  # in liters
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)

class SleepLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    hours = db.Column(db.Float, nullable=False)
    quality = db.Column(db.String(20))
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)

class MoodLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    mood = db.Column(db.String(50), nullable=False)
    notes = db.Column(db.Text)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)

class Goal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    goal_type = db.Column(db.String(100), nullable=False)
    target = db.Column(db.String(100), nullable=False)
    current_value = db.Column(db.Float, default=0)
    target_value = db.Column(db.Float)
    unit = db.Column(db.String(20))
    deadline = db.Column(db.DateTime)
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        name = request.form['name']
        age = int(request.form['age'])
        height = float(request.form['height'])
        weight = float(request.form['weight'])
        gender = request.form['gender']
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists!')
            return redirect(url_for('register'))
        
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            name=name,
            age=age,
            height=height,
            weight=weight,
            gender=gender
        )
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password!')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Calculate current BMI
    height_m = current_user.height / 100
    current_bmi = current_user.weight / (height_m ** 2)
    
    # Calculate daily calories needed
    if current_user.gender == 'male':
        bmr = (13.75 * current_user.weight) + (5 * current_user.height) - (6.76 * current_user.age) + 66
    else:
        bmr = (9.56 * current_user.weight) + (1.85 * current_user.height) - (4.68 * current_user.age) + 655
    
    # Get recent data
    recent_exercise = ExerciseLog.query.filter_by(user_id=current_user.id).order_by(ExerciseLog.recorded_at.desc()).limit(5).all()
    recent_water = WaterLog.query.filter_by(user_id=current_user.id).order_by(WaterLog.recorded_at.desc()).limit(5).all()
    recent_sleep = SleepLog.query.filter_by(user_id=current_user.id).order_by(SleepLog.recorded_at.desc()).limit(5).all()
    
    # Calculate today's totals
    today = datetime.now().date()
    today_water = sum(log.amount for log in recent_water if log.recorded_at.date() == today)
    today_exercise = sum(log.duration for log in recent_exercise if log.recorded_at.date() == today)
    today_sleep = sum(log.hours for log in recent_sleep if log.recorded_at.date() == today)
    
    return render_template('dashboard.html', 
                         user=current_user, 
                         bmi=current_bmi, 
                         daily_calories=bmr,
                         today_water=today_water,
                         today_exercise=today_exercise,
                         today_sleep=today_sleep)

@app.route('/bmi_calculator')
@login_required
def bmi_calculator():
    height_m = current_user.height / 100
    current_bmi = current_user.weight / (height_m ** 2)
    
    # Determine BMI category
    if current_user.gender == 'male':
        if current_bmi < 18.5:
            category = 'Underweight'
            advice = ['Consult a healthcare professional', 'Increase caloric intake', 'Eat frequently', 'Focus on nutrient-rich foods', 'Strength training', 'Stay hydrated', 'Avoid excessive junk food']
        elif 18.5 <= current_bmi < 25:
            category = 'Healthy Weight'
            advice = ['Maintain your current healthy lifestyle', 'Regular exercise', 'Balanced diet', 'Regular health checkups']
        elif 25 <= current_bmi < 30:
            category = 'Overweight'
            advice = ['Set realistic goals', 'Focus on nutrition', 'Control portion sizes', 'Eat mindfully', 'Stay hydrated', 'Incorporate physical activity', 'Get enough sleep']
        else:
            category = 'Obese'
            advice = ['Consult a healthcare professional', 'Create a structured weight loss plan', 'Regular exercise', 'Balanced diet', 'Regular health checkups']
    else:
        if current_bmi < 18.5:
            category = 'Underweight'
            advice = ['Consult a healthcare professional', 'Increase caloric intake', 'Eat frequently', 'Focus on nutrient-rich foods', 'Strength training', 'Stay hydrated', 'Avoid excessive junk food']
        elif 18.5 <= current_bmi < 24:
            category = 'Healthy Weight'
            advice = ['Maintain your current healthy lifestyle', 'Regular exercise', 'Balanced diet', 'Regular health checkups']
        elif 24 <= current_bmi < 29:
            category = 'Overweight'
            advice = ['Set realistic goals', 'Focus on nutrition', 'Control portion sizes', 'Eat mindfully', 'Stay hydrated', 'Incorporate physical activity', 'Get enough sleep']
        else:
            category = 'Obese'
            advice = ['Consult a healthcare professional', 'Create a structured weight loss plan', 'Regular exercise', 'Balanced diet', 'Regular health checkups']
    
    return render_template('bmi_calculator.html', bmi=current_bmi, category=category, advice=advice)

@app.route('/exercise_tracker', methods=['GET', 'POST'])
@login_required
def exercise_tracker():
    if request.method == 'POST':
        exercise_type = request.form['exercise_type']
        duration = int(request.form['duration'])
        intensity = request.form['intensity']
        
        # Calculate calories burned (rough estimate)
        calories_burned = duration * 5 if intensity == 'low' else duration * 8 if intensity == 'medium' else duration * 12
        
        exercise_log = ExerciseLog(
            user_id=current_user.id,
            exercise_type=exercise_type,
            duration=duration,
            intensity=intensity,
            calories_burned=calories_burned
        )
        
        db.session.add(exercise_log)
        db.session.commit()
        
        flash('Exercise logged successfully!')
        return redirect(url_for('exercise_tracker'))
    
    exercise_logs = ExerciseLog.query.filter_by(user_id=current_user.id).order_by(ExerciseLog.recorded_at.desc()).all()
    return render_template('exercise_tracker.html', exercise_logs=exercise_logs)

@app.route('/water_tracker', methods=['GET', 'POST'])
@login_required
def water_tracker():
    if request.method == 'POST':
        amount = float(request.form['amount'])
        
        water_log = WaterLog(
            user_id=current_user.id,
            amount=amount
        )
        
        db.session.add(water_log)
        db.session.commit()
        
        flash('Water intake logged successfully!')
        return redirect(url_for('water_tracker'))
    
    water_logs = WaterLog.query.filter_by(user_id=current_user.id).order_by(WaterLog.recorded_at.desc()).all()
    today_water = sum(log.amount for log in water_logs if log.recorded_at.date() == datetime.now().date())
    target_water = 2.5  # Default target in liters
    
    return render_template('water_tracker.html', water_logs=water_logs, today_water=today_water, target_water=target_water)

@app.route('/sleep_tracker', methods=['GET', 'POST'])
@login_required
def sleep_tracker():
    if request.method == 'POST':
        hours = float(request.form['hours'])
        quality = request.form['quality']
        
        sleep_log = SleepLog(
            user_id=current_user.id,
            hours=hours,
            quality=quality
        )
        
        db.session.add(sleep_log)
        db.session.commit()
        
        flash('Sleep logged successfully!')
        return redirect(url_for('sleep_tracker'))
    
    sleep_logs = SleepLog.query.filter_by(user_id=current_user.id).order_by(SleepLog.recorded_at.desc()).all()
    return render_template('sleep_tracker.html', sleep_logs=sleep_logs)

@app.route('/mood_tracker', methods=['GET', 'POST'])
@login_required
def mood_tracker():
    if request.method == 'POST':
        mood = request.form['mood']
        notes = request.form['notes']
        
        mood_log = MoodLog(
            user_id=current_user.id,
            mood=mood,
            notes=notes
        )
        
        db.session.add(mood_log)
        db.session.commit()
        
        flash('Mood logged successfully!')
        return redirect(url_for('mood_tracker'))
    
    mood_logs = MoodLog.query.filter_by(user_id=current_user.id).order_by(MoodLog.recorded_at.desc()).all()
    return render_template('mood_tracker.html', mood_logs=mood_logs)

@app.route('/goals', methods=['GET', 'POST'])
@login_required
def goals():
    if request.method == 'POST':
        goal_type = request.form['goal_type']
        target = request.form['target']
        target_value = float(request.form['target_value'])
        unit = request.form['unit']
        deadline_str = request.form['deadline']
        
        deadline = datetime.strptime(deadline_str, '%Y-%m-%d') if deadline_str else None
        
        goal = Goal(
            user_id=current_user.id,
            goal_type=goal_type,
            target=target,
            target_value=target_value,
            unit=unit,
            deadline=deadline
        )
        
        db.session.add(goal)
        db.session.commit()
        
        flash('Goal set successfully!')
        return redirect(url_for('goals'))
    
    goals = Goal.query.filter_by(user_id=current_user.id).order_by(Goal.created_at.desc()).all()
    return render_template('goals.html', goals=goals, datetime=datetime)

@app.route('/update_goal/<int:goal_id>', methods=['POST'])
@login_required
def update_goal(goal_id):
    goal = Goal.query.get_or_404(goal_id)
    if goal.user_id != current_user.id:
        flash('Unauthorized access!')
        return redirect(url_for('goals'))
    
    current_value = float(request.form['current_value'])
    goal.current_value = current_value
    
    if current_value >= goal.target_value:
        goal.completed = True
    
    db.session.commit()
    flash('Goal updated successfully!')
    return redirect(url_for('goals'))


@app.route('/progress')
@login_required
def progress():
    # Get data for charts
    exercise_data = db.session.query(
        db.func.date(ExerciseLog.recorded_at).label('date'),
        db.func.sum(ExerciseLog.duration).label('total_duration')
    ).filter_by(user_id=current_user.id).group_by(db.func.date(ExerciseLog.recorded_at)).order_by(db.func.date(ExerciseLog.recorded_at).desc()).limit(30).all()
    
    water_data = db.session.query(
        db.func.date(WaterLog.recorded_at).label('date'),
        db.func.sum(WaterLog.amount).label('total_water')
    ).filter_by(user_id=current_user.id).group_by(db.func.date(WaterLog.recorded_at)).order_by(db.func.date(WaterLog.recorded_at).desc()).limit(30).all()
    
    sleep_data = db.session.query(
        db.func.date(SleepLog.recorded_at).label('date'),
        db.func.avg(SleepLog.hours).label('avg_sleep')
    ).filter_by(user_id=current_user.id).group_by(db.func.date(SleepLog.recorded_at)).order_by(db.func.date(SleepLog.recorded_at).desc()).limit(30).all()
    
    return render_template('progress.html', 
                         exercise_data=exercise_data,
                         water_data=water_data,
                         sleep_data=sleep_data)




if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)