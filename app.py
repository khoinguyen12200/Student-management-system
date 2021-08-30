from flask import Flask, jsonify, request
import pymysql
from pymysql.cursors import DictCursor
from datetime import timedelta
import json

from flask_jwt_extended import create_access_token
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended import jwt_required
from flask_jwt_extended import JWTManager
from flask_jwt_extended import set_access_cookies

prod = False

app = Flask(__name__)

app.config["JWT_SECRET_KEY"] = "my-super-secret"  # Change this!
# app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
# app.config["JWT_TOKEN_LOCATION"] =  ['headers', 'query_string']
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=10)
jwt = JWTManager(app)


connection = pymysql.connect(
    host="localhost",
    user="root",
    password="",
    database="htqlsv",
    cursorclass=DictCursor
)

@app.after_request
def commit(res):
    connection.commit()
    return res



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

    cursor.execute(
        "SELECT * FROM manager where account = %s and password = %s", [account, password])
    result = cursor.fetchone()
  

    cursor.close()

    if(result == None):
        return jsonify({"e": True, "m": "Tài khoản mật khẩu không khớp"})


    access_token = create_access_token(identity=account)
    response = jsonify({"m": "Đăng nhập thành công", "info": result,"token": access_token})
    app.logger.info(response.get_json())
    return response


@app.get("/api/manager/auto-login")
@jwt_required()
def auto_login():
    account = get_jwt_identity()
    app.logger.info(account)
    if(account != None):
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM manager where ACCOUNT = %s", [account])
        info = cursor.fetchone()
        cursor.close()
        if(info != None):
            return jsonify({"info": info})

    return jsonify({"e": True})


@app.post("/api/manager/change-password")
@jwt_required()
def changePassword():
    account = get_jwt_identity()
    cursor = connection.cursor()

    body = request.get_json()
    newPassword = body['newPassword']
    oldPassword = body['oldPassword']

    updated = cursor.execute("UPDATE manager set PASSWORD = %s where ACCOUNT = %s and PASSWORD = %s", [
                   newPassword, account, oldPassword])
    cursor.close()

    if(updated != 0) :
        return jsonify({"m": "Đổi mật khẩu thành công"})
    else :
        return jsonify({"e":True,"m": "Lỗi xảy ra, không có gì thay đổi"})

@app.post("/api/manager/change-name")
@jwt_required()
def changeName():
    account = get_jwt_identity()
    cursor = connection.cursor()

    body = request.get_json()
    newName = body['newName']
    password = body['password']

    updated = cursor.execute("UPDATE manager set FULL_NAME = %s where ACCOUNT = %s and PASSWORD = %s", [
                   newName, account, password])
    cursor.close()

    if(updated != 0) :
        return jsonify({"m": "Đổi tên thành công"})
    else :
        return jsonify({"e":True,"m": "Lỗi xảy ra, không có gì thay đổi"})


@app.get("/api/manager/department")
@jwt_required()
def getDepartment():
    account = get_jwt_identity()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM department WHERE 1")
    departments = cursor.fetchall()
    return jsonify(departments)


# insertDepartment name sortName
@app.post("/api/manager/department/insert")
@jwt_required()
def insertDepartment():
    account = get_jwt_identity()
    cursor = connection.cursor()

    body = request.get_json()
    name = body['name']
    sortName = body['sortName']
    id = body.get('id')
    print(str(id))
    insert = 0
    if(id != None):
        insert = cursor.execute("INSERT INTO `department`(`id`,`NAME`, `SORT_NAME`) VALUES (%s,%s,%s)", [id,name,sortName])
    else :
        insert = cursor.execute("INSERT INTO `department`(`NAME`, `SORT_NAME`) VALUES (%s,%s)", [name,sortName])

    

    cursor.close()
    if(insert != 0) :
        return jsonify({"m": "Thêm thành công"})
    else :
        return jsonify({"e":True,"m": "Lỗi xảy ra, không có gì thay đổi"})

# updateDepartment id name | sortName
@app.post("/api/manager/department/update")
@jwt_required()
def updateDepartment():
    account = get_jwt_identity()
    cursor = connection.cursor()

    body = request.get_json()
   
    id = body.get("id")
    newId = body.get("newId")
    name = body.get("name")
    sortName = body.get("sortName")

    numberChange = 0

    if(name):
        changed = cursor.execute("UPDATE `department` set NAME = %s where id = %s", [name,id])
        numberChange += changed

    if(sortName):
        changed = cursor.execute("UPDATE `department` set SORT_NAME = %s where id = %s", [sortName,id])
        numberChange += changed

    if(newId):
        changed = cursor.execute("UPDATE `department` set ID = %s where id = %s", [newId,id])
        numberChange += changed
    
    cursor.close()
    connection.commit()

    if(numberChange != 0) :
        return jsonify({"m": "Có "+str(numberChange)+" thay đổi được cập nhật"})
    else :
        return jsonify({"e":True,"m": "Lỗi xảy ra, không có gì thay đổi"})

# id
@app.post("/api/manager/department/delete")
@jwt_required()
def deleteDepartment():
    account = get_jwt_identity()
    cursor = connection.cursor()

    body = request.get_json()
    id = body.get("id")
    password = body.get("password")

    cursor.execute("select * from manager where ACCOUNT = %s and PASSWORD = %s",[account,password])
    user = cursor.fetchone()
    if(user == None):
        return jsonify({"e":True,"m": "Sai mật khẩu xác nhận"})

    deleted = cursor.execute("DELETE from `department` where ID = %s", [id])
    cursor.close()

    if(deleted != 0) :
        return jsonify({"m": "Xóa thành công"})
    else :
        return jsonify({"e":True,"m": "Lỗi xảy ra, không có gì thay đổi"})


if __name__ == "__main__":
    if prod:
        app.run()
    else:
        app.run(debug=True)
