from flask import Flask, render_template, request, redirect, url_for, flash, get_flashed_messages,session
from pymongo import MongoClient
from datetime import datetime
from bson.objectid import ObjectId
import secrets


app = Flask(__name__)
app.secret_key = secrets.token_hex(16) 

mongo_uri = "mongodb+srv://MediBuddyUser:MediBuddy2025@medibuddy.346h16q.mongodb.net/?retryWrites=true&w=majority&appName=MediBuddy"


client = MongoClient(mongo_uri)

db = client['medibuddy_db']
students = db['students']
health_records = db['health_records']


@app.route('/')
def information():
    messages = get_flashed_messages()
    return render_template('information.html', messages=messages)


@app.route('/move', methods=['POST', 'GET'])
def move():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        student_id = request.form.get('studentnumber', '').strip()
        password = request.form.get('password', '').strip()

        matched_student = students.find_one({
            'student_id': student_id,
            'name': name,
            'password': password
        })

        if not matched_student:
            flash("학번 또는 비밀번호가 틀렸습니다.")
            return redirect(url_for('information'))

        session['current_record'] = {
            "student_id": student_id,
            "name": name,
            "date": datetime.now().isoformat(),
            "is_root": (name == 'root')
        }

        if name == 'root':
            return redirect(url_for('list_records'))

        return redirect(url_for('move'))

    record = session.get('current_record')
    if not record:
        return redirect(url_for('information'))

    select = request.args.get('select')
    if select == 'reservation':
        return redirect(url_for('cure_method'))
    elif select == 'nurseInfo':
        student_id = record.get("student_id")
        if not student_id:
            flash("학생 정보가 유실되었습니다. 다시 로그인해주세요.")
            return redirect(url_for('information'))
        return redirect(url_for('studentlist', student_id=student_id))

    return render_template('main.html', name=record["name"], student_id=record["student_id"])

@app.route('/cure_method', methods=['GET', 'POST'])
def cure_method():
    if request.method == 'POST':
        treatment_str = request.form.get('treatment')

        if 'current_record' not in session:
            flash("저장된 환자 정보가 없습니다.", "error")
            return redirect(url_for('information'))

        treatment_bool = treatment_str == 'true'

        record = session.get('current_record')
        record['treatment'] = treatment_bool
        session['current_record'] = record

        return redirect(url_for('symptoms'))

    return render_template('cure_method.html')

@app.route('/symptoms', methods=['GET', 'POST'])
def symptoms():
    if request.method == 'POST':
        symptoms = request.form.get('symptoms')

        if 'current_record' not in session:
            flash("저장된 환자 정보가 없습니다.", "error")
            return redirect(url_for('information')) 

        record = session['current_record']
        symptom_checked = bool(symptoms and symptoms.strip())

        health_records.insert_one({
            "date": record['date'],
            "student_id": record['student_id'],
            "name": record['name'],
            "treatment": record.get('treatment', ''),
            "symptom_checked": symptom_checked,
            "symptoms": symptoms,
            "confirmation": False
        })

        return redirect(url_for('final'))

    return render_template('symptoms.html')

@app.route('/final', methods=['GET'])
def final():
    if 'current_record' not in session:
        flash("로그인이 필요합니다.")
        return redirect(url_for('information'))

    return render_template('final.html')

@app.route('/list', methods=['GET', 'POST'])
def list_records():
    record = session.get('current_record')
    if not record or not record.get('is_root'):
        return redirect(url_for('move'))

    if request.method == 'POST':
        delete_ids = request.form.getlist('delete_ids')
        if delete_ids:
            try:
                object_ids = [ObjectId(id) for id in delete_ids]
                health_records.update_many(
                    {"_id": {"$in": object_ids}},
                    {"$set": {"confirmation": True}}
                )
            except Exception as e:
                flash("잘못된 아이디가 포함되어 처리할 수 없습니다.")
            return redirect(url_for('list_records'))

    query = {"confirmation": False}
    records = list(health_records.find(query).sort("date", -1))

    for record in records:
        record['_id'] = str(record['_id'])
        if 'date' in record:
            if isinstance(record['date'], datetime):
                record['date'] = record['date'].strftime("%Y-%m-%d")
            else:
                try:
                    parsed_date = datetime.fromisoformat(record['date'])
                    record['date'] = parsed_date.strftime("%Y-%m-%d")
                except Exception:
                    pass

    return render_template('list.html', reservations=records)


@app.route('/studentlist', methods=['GET', 'POST'])
def studentlist():
    record = session.get('current_record')
    if not record:
        flash("로그인이 필요합니다.")
        return redirect(url_for('information'))
    
    if request.method == 'POST':
        return redirect(url_for('move'))

    student_id = request.args.get('student_id')
    if request.method == 'POST':
        student_id = request.form.get('student_id', student_id)

    if not student_id:
        return "학번이 전달되지 않았습니다.", 400

    if student_id != record.get('student_id'):
        return redirect(url_for('move'))

    query = {"student_id": student_id}
    records = list(health_records.find(query).sort("date", -1))

    for record in records:
        record['_id'] = str(record['_id'])
        if 'date' in record:
            if isinstance(record['date'], datetime):
                record['date'] = record['date'].strftime("%Y-%m-%d")
            else:
                try:
                    parsed_date = datetime.fromisoformat(record['date'])
                    record['date'] = parsed_date.strftime("%Y-%m-%d")
                except Exception:
                    pass

    return render_template('studentlist.html', reservations=records, student_id=student_id)


@app.route('/delete_all', methods=['POST'])
def delete_all():
    health_records.delete_many({})
    return redirect(url_for('list_records'))


@app.route('/editpassword', methods=['GET'])
def editpassword():
    if 'current_record' not in session:
        flash("정보를 먼저 입력해주세요.")
        return redirect(url_for('information'))

    return render_template('editPass.html')

@app.route('/change_password', methods=['POST'])
def change_password():
    current_pass = request.form.get('currentPass', '').strip()
    new_pass = request.form.get('newPass', '').strip()
    
    record = session.get('current_record')
    if not record:
        flash("로그인이 필요합니다.")
        return redirect(url_for('information'))
    
    student_id = record.get('student_id')

    student = students.find_one({'student_id': student_id})

    if not student or student.get('password') != current_pass:
        flash("현재 비밀번호가 틀렸습니다.")
        return redirect(url_for('editpassword'))

    students.update_one({'student_id': student_id}, {'$set': {'password': new_pass}})

    flash("비밀번호가 성공적으로 변경되었습니다.")
    return redirect(url_for('information'))

@app.route('/logout')
def logout():
    session.clear()
    flash("로그아웃되었습니다.")
    return redirect(url_for('information')) 


if __name__ == '__main__':
    app.run(debug=True,port=5001)