from flask import Flask, jsonify, request
import pymysql
from pymysql.cursors import DictCursor
from datetime import timedelta
import json
import mysql.connector
import mysql.connector.pooling
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


pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="mypool",
    pool_size=10,
    autocommit=True,
    host="localhost",
    user='root',
    password="",
    database='htqlsv')


def sqlExecute(sql, args=[], fetch=0):
    try:
        connection = pool.get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sql, args)

        result = None
        if(fetch == 0):
            result = cursor.rowcount
        if(fetch == 1):
            result = cursor.fetchone()
        if(fetch > 1):
            result = cursor.fetchall()

        cursor.close()
        connection.close()
        return result
    except Exception as e:
        print("Error in sql: " + sql + str(e))
        return 0


@app.route("/")
def main():
    return "Welcome!"


@app.post("/api/manager/login")
def sign_in():

    data = request.get_json()
    account = data['account']
    password = data['password']

    user = sqlExecute(
        "SELECT * FROM manager where ACCOUNT = %s and PASSWORD = %s", [account, password], 1)

    if(user == None):
        return jsonify({"e": True, "m": "Tài khoản mật khẩu không khớp"})

    access_token = create_access_token(identity=account)
    response = jsonify({"m": "Đăng nhập thành công",
                       "info": user, "token": access_token})
    app.logger.info(response.get_json())
    return response


@app.get("/api/manager/auto-login")
@jwt_required()
def auto_login():
    account = get_jwt_identity()
    app.logger.info(account)
    if(account != None):

        info = sqlExecute(
            "SELECT * FROM manager where ACCOUNT = %s;", [account], 1)

        if(info != None):
            return jsonify({"info": info})

    return jsonify({"e": True})


@app.post("/api/manager/change-password")
@jwt_required()
def changePassword():
    account = get_jwt_identity()

    body = request.get_json()
    newPassword = body['newPassword']
    oldPassword = body['oldPassword']

    updated = sqlExecute("UPDATE manager set PASSWORD = %s where ACCOUNT = %s and PASSWORD = %s", [
        newPassword, account, oldPassword])

    if(updated != 0):
        return jsonify({"m": "Đổi mật khẩu thành công"})
    else:
        return jsonify({"e": True, "m": "Lỗi xảy ra, không có gì thay đổi"})


@app.post("/api/manager/change-name")
@jwt_required()
def changeName():
    account = get_jwt_identity()

    body = request.get_json()
    newName = body['newName']
    password = body['password']

    updated = sqlExecute("UPDATE manager set FULL_NAME = %s where ACCOUNT = %s and PASSWORD = %s", [
        newName, account, password])

    if(updated != 0):
        return jsonify({"m": "Đổi tên thành công"})
    else:
        return jsonify({"e": True, "m": "Lỗi xảy ra, không có gì thay đổi"})


# KHOA

@app.get("/api/manager/department")
@jwt_required()
def getDepartment():
    account = get_jwt_identity()
    departments = sqlExecute("SELECT * FROM `department` WHERE 1", [], 2)

    return jsonify(departments)


# insertDepartment name sortName
@app.post("/api/manager/department/insert")
@jwt_required()
def insertDepartment():
    account = get_jwt_identity()

    body = request.get_json()
    name = body['name']
    sortName = body['sortName']
    id = body.get('id')
    print(str(id))
    insert = 0

    if(id != None):
        insert = sqlExecute("INSERT INTO `department`(`id`,`NAME`, `SORT_NAME`) VALUES (%s,%s,%s)", [
                            id, name, sortName])
    else:
        insert = sqlExecute(
            "INSERT INTO `department`(`NAME`, `SORT_NAME`) VALUES (%s,%s)", [name, sortName])

    if(insert != 0):
        return jsonify({"m": "Thêm thành công"})
    else:
        return jsonify({"e": True, "m": "Lỗi xảy ra, không có gì thay đổi"})


@app.post("/api/manager/department/update")
@jwt_required()
def updateDepartment():
    account = get_jwt_identity()
    body = request.get_json()

    id = body.get("id")
    newId = body.get("newId")
    name = body.get("name")
    sortName = body.get("sortName")

    numberChange = 0

    if(name):
        changed = sqlExecute(
            "UPDATE `department` set NAME = %s where id = %s", [name, id])
        numberChange += changed

    if(sortName):
        changed = sqlExecute(
            "UPDATE `department` set SORT_NAME = %s where id = %s", [sortName, id])
        numberChange += changed

    if(newId):
        changed = sqlExecute(
            "UPDATE `department` set ID = %s where id = %s", [newId, id])
        numberChange += changed

    if(numberChange != 0):
        return jsonify({"m": "Có "+str(numberChange)+" thay đổi được cập nhật"})
    else:
        return jsonify({"e": True, "m": "Lỗi xảy ra, không có gì thay đổi"})


@app.post("/api/manager/department/delete")
@jwt_required()
def deleteDepartment():
    account = get_jwt_identity()
    body = request.get_json()
    id = body.get("id")
    password = body.get("password")

    user = sqlExecute(
        "select * from manager where ACCOUNT = %s and PASSWORD = %s", [account, password], 1)

    if(user == None):
        return jsonify({"e": True, "m": "Sai mật khẩu xác nhận"})

    deleted = sqlExecute("DELETE from `department` where ID = %s", [id])

    if(deleted == 0):
        return jsonify({"m": "Xóa thành công"})
    else:
        return jsonify({"e": True, "m": "Lỗi xảy ra, không có gì thay đổi"})


########################## CHUYÊN NGÀNH ##########################

@app.get("/api/manager/major")
@jwt_required()
def getMajor():

    majors = sqlExecute("SELECT * FROM `major` where 1", [], 2)
    return jsonify(majors)


@app.post("/api/manager/major/insert")
@jwt_required()
def insertMajor():

    body = request.get_json()
    id = body.get("id")
    name = body.get("name")
    sortName = body.get("sortName")
    department = body.get("department")

    insert = 0

    if(id == None):
        insert = sqlExecute("INSERT INTO `major`(`NAME`, `SORT_NAME`, `DEPARTMENT`) VALUES (%s,%s,%s)", [
            name, sortName, department])
    else:
        insert = sqlExecute("INSERT INTO `major`(`ID`, `NAME`, `SORT_NAME`, `DEPARTMENT`) VALUES (%s,%s,%s,%s)", [
                            id, name, sortName, department])

    if(insert != 0):
        return jsonify({"m": "Đã thêm thành công"})
    return jsonify({"e": True, "m": "Có lỗi xảy ra"})


@app.post("/api/manager/major/update")
@jwt_required()
def updatetMajor():

    body = request.get_json()
    id = body.get("id")
    newId = body.get("newId")
    name = body.get("name")
    sortName = body.get("sortName")
    department = body.get("department")

    updated = 0

    if(newId != None):
        update = sqlExecute(
            "update major set ID = %s where ID = %s", [newId, id])
        updated += update
    if(name != None):
        update = sqlExecute(
            "update major set NAME = %s where ID = %s", [name, id])
        updated += update
    if(sortName != None):
        update = sqlExecute(
            "update major set SORT_NAME = %s where ID = %s", [sortName, id])
        updated += update
    if(department != None):
        update = sqlExecute(
            "update major set DEPARTMENT = %s where ID = %s", [department, id])
        updated += update

    if(updated != 0):
        return jsonify({"m": 'Đã thay đổi '+str(updated)+' giá trị'})
    return jsonify({"e": True, "m": "Có lỗi xảy ra"})


@app.post("/api/manager/major/delete")
@jwt_required()
def deleteMajor():
    account = get_jwt_identity()
    body = request.get_json()
    id = body.get("id")
    password = body.get("password")

    user = sqlExecute(
        "SELECT * from manager where ACCOUNT = %s and PASSWORD = %s", [account, password], 1)

    if(user == None):
        return jsonify({"e": True, "m": "Xác nhận mật khẩu sai"})

    delete = sqlExecute("DELETE FROM major where ID = %s", [id])
    if(delete == 0):
        return jsonify({"e": True, "m": "Xóa không thành công"})
    return jsonify({"m": "Xóa thành công"})


########################## LỚP CHUYÊN NGÀNH ##########################


@app.get("/api/class-major")
@jwt_required()
def getClassMajor():

    majors = sqlExecute("SELECT * FROM `class` where 1 order by NAME", [], 2)
    return jsonify(majors)


@app.post("/api/class-major/insert")
@jwt_required()
def insertClassMajor():

    body = request.get_json()
    name = body.get("name")
    major = body.get("major")
    course = body.get("course")
    instructor = body.get("instructor")

    insert = 0

    print("instructor")
    print(str(instructor))

    insert = sqlExecute("INSERT INTO `class`(`NAME`, `MAJOR`, `COURSE`, `INSTRUCTOR`) VALUES (%s,%s,%s,%s)", [
            name, major, course,instructor])

    if(insert != 0):
        return jsonify({"m": "Đã thêm thành công"})
    return jsonify({"e": True, "m": "Có lỗi xảy ra"})


@app.post("/api/class-major/update")
@jwt_required()
def updateClassMajor():

    body = request.get_json()
    id = body.get("id")
    name = body.get("name")
    major = body.get("major")
    course = body.get("course")
    instructor = body.get("instructor")

    

    updated = sqlExecute(
        "update class set MAJOR = %s, NAME = %s, COURSE = %s, INSTRUCTOR = %s where ID = %s",
         [major,name,course,instructor, id])

    if(updated != 0):
        return jsonify({"m": 'Đã thay đổi thành công'})
    return jsonify({"e": True, "m": "Có lỗi xảy ra"})


@app.post("/api/class-major/delete")
@jwt_required()
def deleteClassMajor():
    account = get_jwt_identity()
    body = request.get_json()
    id = body.get("id")
    password = body.get("password")

    user = sqlExecute(
        "SELECT * from manager where ACCOUNT = %s and PASSWORD = %s", [account, password], 1)

    if(user == None):
        return jsonify({"e": True, "m": "Xác nhận mật khẩu sai"})

    delete = sqlExecute("DELETE FROM class where ID = %s", [id])
    if(delete == 0):
        return jsonify({"e": True, "m": "Xóa không thành công"})
    return jsonify({"m": "Xóa thành công"})


@app.get("/api/instructor")
@jwt_required()
def getInstructor():
    account = get_jwt_identity()
    body = request.get_json()

    result = sqlExecute("select * from instructor where 1",[],2)
    return jsonify(result)

@app.post("/api/instructor")
@jwt_required()
def postInstructor():
    account = get_jwt_identity()
    body = request.get_json()
    instructorId = body.get('instructorId')
    fullName = body.get("fullName")
    dateOfBirth = body.get("dateOfBirth")
    gender = body.get("gender")
    citizenId = body.get("citizenId")

    addResult = sqlExecute("INSERT INTO `instructor`(`INSTRUCTOR_ID`,`FULL_NAME`, `DATE_OF_BIRTH`, `GENDER`, `CITIZEN_ID`) VALUES (%s,%s,%s,%s,%s)"
    , [instructorId,fullName,dateOfBirth,gender,citizenId])
    if(addResult):
        return jsonify({"m":"Thêm thành công"})

    print(addResult)
    return jsonify({"m":"Có lỗi xảy ra","e": True})


@app.put("/api/instructor")
@jwt_required()
def putInstructor():
    account = get_jwt_identity()
    body = request.get_json()
    id = body.get("id")
    instructorId = body.get('instructorId')
    fullName = body.get("fullName")
    dateOfBirth = body.get("dateOfBirth")
    gender = body.get("gender")
    citizenId = body.get("citizenId")

    updateResult = sqlExecute("UPDATE `instructor` SET `INSTRUCTOR_ID`=%s,`FULL_NAME`=%s,`DATE_OF_BIRTH`=%s,`GENDER`=%s,`CITIZEN_ID`=%s WHERE ID = %s"
    , [instructorId,fullName,dateOfBirth,gender,citizenId,id])
    if(updateResult):
        return jsonify({"m":"Thay đổi đã lưu thành công"})

    print(updateResult)
    return jsonify({"m":"Có lỗi xảy ra","e": True})

@app.delete("/api/instructor")
@jwt_required()
def deleteInstructor():
    account = get_jwt_identity()
    body = request.get_json()
    id = body.get("id")
    password = body.get("password")

    user = sqlExecute(
        "SELECT * from manager where ACCOUNT = %s and PASSWORD = %s", [account, password], 1)

    if(user == None):
        return jsonify({"e": True, "m": "Xác nhận mật khẩu sai"})

    deleteResult = sqlExecute("DELETE FROM instructor where ID = %s",[id])
    if(deleteResult):
        return jsonify({"m":"Xóa thành công"})

    print(deleteResult)
    return jsonify({"m":"Có lỗi xảy ra","e": True})


if __name__ == "__main__":
    if prod:
        app.run()
    else:
        app.run(debug=True)
