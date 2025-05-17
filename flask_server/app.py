from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# ✅ 여기에 너의 MySQL 주소를 입력해야 해!
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:1013@localhost/medibuddy_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ✅ 예약 테이블 모델 정의
class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    grade = db.Column(db.String(10))
    ban = db.Column(db.String(10))
    number = db.Column(db.String(10))
    is_self = db.Column(db.Boolean)
    symptoms = db.Column(db.String(200))

# ✅ 최초 실행 시 테이블 생성
with app.app_context():
    db.create_all()

# 페이지 라우팅
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/move', methods=['POST'])
def move():
    select = request.form['select']
    if select == 'reservation':
        return render_template('information.html')

@app.route('/information', methods=['GET', 'POST'])
def information():
    if request.method == 'POST':
        name = request.form['name']
        grade = request.form['grade']
        ban = request.form['ban']
        number = request.form['number']

        # DB에 새 예약 생성, 일단 is_self/symptoms는 None
        new_reservation = Reservation(
            name=name,
            grade=grade,
            ban=ban,
            number=number,
            is_self=None,
            symptoms=None
        )
        db.session.add(new_reservation)
        db.session.commit()
        return render_template('cure_method.html')

    return render_template('information.html')

@app.route('/cure_method', methods=['GET', 'POST'])
def cure_method():
    if request.method == 'POST':
        is_self = request.form['isSelf']
        latest = Reservation.query.order_by(Reservation.id.desc()).first()

        if latest:
            latest.is_self = (is_self == 'true')
            db.session.commit()
            return render_template('symptoms.html')
        else:
            return "저장할 예약 정보가 없습니다.", 400

    return render_template('cure_method.html')

@app.route('/symptoms', methods=['GET', 'POST'])
def symptoms():
    if request.method == 'POST':
        symptoms = request.form['symptoms']
        latest = Reservation.query.order_by(Reservation.id.desc()).first()

        if latest:
            latest.symptoms = symptoms
            db.session.commit()
            return render_template('final.html')
        else:
            return "저장할 예약 정보가 없습니다.", 400

    return render_template('final.html')

@app.route('/final')
def final():
    return render_template('final.html')

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1')
