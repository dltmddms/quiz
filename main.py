from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash
import random

app = Flask(__name__, template_folder='templates')
app.secret_key = 'your_secret_key'

# 사용자 정보를 저장할 데이터베이스 설정
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'  # 사용자 정보를 저장할 데이터베이스
app.config['SQLALCHEMY_BINDS'] = {
    'quiz': 'sqlite:///users.db'  # 퀴즈 정보를 저장할 데이터베이스
}
db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

class Quiz(db.Model):
    __bind_key__ = 'quiz'
    __tablename__ = 'quiz'
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    options = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Integer, nullable=False)


# 퀴즈 데이터 추가 (중복 데이터 추가 방지)
def add_quiz_data():
    existing_questions = Quiz.query.all()
    existing_questions_text = [q.question for q in existing_questions]

    questions = [
        {"question": "What is the capital of France?", "options": "A. Paris, B. Rome, C. London, D. Berlin", "answer": 1},
        {"question": "Which planet is known as the Red Planet?", "options": "A. Venus, B. Mars, C. Jupiter, D. Saturn", "answer": 2},
        {"question": "Who wrote 'Romeo and Juliet'?", "options": "A. William Shakespeare, B. Charles Dickens, C. Jane Austen, D. Mark Twain", "answer": 1},
        {"question": "What is the largest ocean on Earth?", "options": "A. Atlantic Ocean, B. Indian Ocean, C. Arctic Ocean, D. Pacific Ocean", "answer": 4},
        {"question": "What is the capital of Japan?", "options": "A. Tokyo, B. Kyoto, C. Osaka, D. Nagoya", "answer": 1},
        {"question": "Who painted the Mona Lisa?", "options": "A. Leonardo da Vinci, B. Pablo Picasso, C. Vincent van Gogh, D. Michelangelo", "answer": 1},
        {"question": "What is the main ingredient in guacamole?", "options": "A. Avocado, B. Tomato, C. Onion, D. Garlic", "answer": 1}
    ]

    for q in questions:
        if q["question"] not in existing_questions_text:
            quiz_question = Quiz(question=q["question"], options=q["options"], answer=q["answer"])
            db.session.add(quiz_question)
            db.session.commit()


# 퀴즈 데이터베이스에 질문 추가
with app.app_context():
    add_quiz_data()

@app.route('/index', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('이미 존재하는 사용자입니다.', 'error')
            return redirect(url_for('login'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)  # 'users' 데이터베이스에 추가
        db.session.commit()
        flash('회원가입이 완료되었습니다. 로그인해주세요.', 'success')
        return redirect(url_for('login'))

    return render_template('index.html')

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user:
            if check_password_hash(user.password, password):
                session['username'] = username
                flash('로그인되었습니다.', 'success')
                session['answered_quiz_ids'] = []
                return redirect(url_for('quiz'))
            else:
                flash('비밀번호가 올바르지 않습니다.', 'error')
                return redirect(url_for('login'))
        else:
            flash('존재하지 않는 사용자입니다. 회원가입을 진행해주세요.', 'error')
            return redirect(url_for('index'))

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'username' in session:
        username = session['username']
        return render_template('dashboard.html', username=username)
    else:
        flash('로그인이 필요합니다.', 'error')
        return redirect(url_for('login'))


@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('로그아웃되었습니다.', 'success')
    return redirect(url_for('login'))

import sys
# 퀴즈 랜덤 선택을 처리하는 함수
def get_random_quiz():
    answered_quiz_ids = session.get('answered_quiz_ids', [])
    answered_quiz_id = session.get('answered_quiz_id')
    all_quiz_ids = [q.id for q in Quiz.query.all()]

    # 모든 퀴즈를 이미 푼 경우
    if len(answered_quiz_ids) == len(all_quiz_ids) and answered_quiz_id is None:
        return None
    
    # 아직 풀지 않은 퀴즈 선택
    if len(answered_quiz_ids) != len(all_quiz_ids):
        remaining_quiz_ids = list(set(all_quiz_ids) - set(answered_quiz_ids))
        random_question_id = random.choice(remaining_quiz_ids)
        random_question = Quiz.query.get(random_question_id)

    if answered_quiz_id is not None:
        random_question = Quiz.query.get(answered_quiz_id)

    return random_question

@app.route('/quiz')
def quiz():
    # 랜덤하게 퀴즈 문제 선택
    question = get_random_quiz()

    # 퀴즈 문제가 없으면 대시보드로 이동
    if question is None:
        session.pop('answered_quiz_ids', None)
        session.pop('submitted', None)
        session.pop('message_type', None)
        session.pop('correct_answer', None)
        session.pop('selected_answer', None)
        
        return render_template('if_finished.html')
        
    options = question.options.split(',')

    # 사용자가 제출한 답변 및 메시지 가져오기
    submitted = session.get('submitted', False)
    message_type = session.get('message_type')
    correct_answer = session.get('correct_answer')
    selected_answer = session.get('selected_answer')

    # 세션 변수 초기화
    session.pop('submitted', None)
    session.pop('message_type', None)
    session.pop('correct_answer', None)
    session.pop('selected_answer', None)
    session.pop('answered_quiz_id', None)

    return render_template('quiz.html', question=question, options=options, submitted=submitted, message_type=message_type, correct_answer=correct_answer, selected_answer=selected_answer)


@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    if request.method == 'POST':
        question_id = request.form['question_id']
        selected_answer = int(request.form.get('answer', -1))

        # 퀴즈 문제 가져오기
        question = Quiz.query.get(question_id)

        # 사용자 답변과 정답 비교
        if question.answer == selected_answer + 1:
            flash('정답입니다!', 'success')
            message_type = 'success'
            correct_answer = None
        else:
            # 틀린 경우 선택된 옵션의 텍스트로 수정
            options = question.options.split(',')
            correct_answer = options[question.answer - 1]
            flash(f'틀렸습니다. 정답은 {correct_answer}입니다.', 'error')
            message_type = 'error'

        # 답변이 제출되었음을 세션에 표시
        session['submitted'] = True
        session['message_type'] = message_type
        session['correct_answer'] = correct_answer
        session['selected_answer'] = selected_answer
        session['answered_quiz_id'] = question_id
        session['answered_quiz_ids'] = session.get('answered_quiz_ids', [])
        session['answered_quiz_ids'].extend([int(question_id)])

    # 문제 페이지로 리디렉션
    return redirect(url_for('quiz'))


@app.route('/next_question')
def next_question():
    session['submitted'] = False
    return redirect(url_for('quiz'))


if __name__ == '__main__':
    app.run(debug=True)
