from flask import Flask, jsonify
from flask_cors import CORS
import pymysql

app = Flask(__name__)
CORS(app)

# Connect to RDS
db = pymysql.connect(
    host='three-tier-db.chk0a6u6g52s.ca-central-1.rds.amazonaws.com',
    user='admin',
    password='*********',
    database='company'
)

@app.route('/')
def home():
    return "<h2>Hello from Flask App on EC2 via ALB!</h2>"

@app.route('/employees')
def employees():
    try:
        cursor = db.cursor()
        cursor.execute("SELECT * FROM employees;")
        rows = cursor.fetchall()
        data = [{"id": r[0], "name": r[1]} for r in rows]
        return jsonify(data)
    except Exception as e:
        return str(e)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
