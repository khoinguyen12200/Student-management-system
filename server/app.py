from flask import Flask, jsonify, request
import pymysql
from pymysql.cursors import DictCursor
from datetime import timedelta

from flask_jwt_extended import create_access_token
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended import jwt_required
from flask_jwt_extended import JWTManager
from flask_jwt_extended import set_access_cookies

prod = False

app = Flask(__name__)

app.config["JWT_SECRET_KEY"] = "my-super-secret"  # Change this!
app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=10)
jwt = JWTManager(app)


connection = pymysql.connect(
    host="localhost",
    user="root",
    password="",
    database="htqlsv",
    cursorclass=DictCursor
)


@app.route("/")
def main():
    return "Welcome!"


@app.post("/api/test")
def abc():
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM student")
    myresult = cursor.fetchall()

    app.logger.info(myresult)
    cursor.close()
    return jsonify(myresult)


@app.post("/api/manager/login")
def sign_in():
    cursor = connection.cursor()

    data = request.get_json()
    account = data['account']
    password = data['password']

    cursor.execute("SELECT * FROM manager where account = %s and password = %s", [account,password])
    result = cursor.fetchone()

    cursor.close()

    if(result == None):
        return jsonify({"e":True,"m":"Tài khoản mật khẩu không khớp"})

    access_token = create_access_token(identity=account)
    response = jsonify({"m": "Đăng nhập thành công","info":result})
    set_access_cookies(response, access_token)
    app.logger.info(response.get_json())
    return response

@app.get("/api/manager/auto-login")
@jwt_required()
def auto_login():
    account = get_jwt_identity()
    app.logger.info(account)
    if(account != None):
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM manager where ACCOUNT = %s",[account])
        info = cursor.fetchone()
        cursor.close()
        if(info != None):
            return jsonify({"info":info})
    
    return jsonify({"e":True})

@app.route("/protected", methods=["GET"])
@jwt_required()
def protected():
    # Access the identity of the current user with get_jwt_identity
    current_user = get_jwt_identity()
    return jsonify(logged_in_as=current_user), 200


if __name__ == "__main__":
    if prod:
        app.run()
    else:
        app.run(debug=True)
