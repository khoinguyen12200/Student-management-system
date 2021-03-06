from flask import Flask, jsonify, request
from datetime import timedelta
import json
import mysql.connector
import mysql.connector.pooling
from flask_jwt_extended import create_access_token
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended import jwt_required
from flask_jwt_extended import JWTManager
from flask_jwt_extended import set_access_cookies
from flask import send_from_directory
from functools import wraps
prod = True

app = Flask(__name__,static_folder="client/build",static_url_path="")
@app.route("/", defaults={'path':''})
def serve(path):
    return send_from_directory(app.static_folder,'index.html')

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

def checkEditable(key):
    def _checkEditable(f):
        @wraps(f)
        def __checkEditable(*args, **kwargs):
            # just do here everything what you need
            result = sqlExecute("select * from editable where 1",[],1)
            checked = result.get(key)
            if(checked == None or checked == False):
                return jsonify({"e": True, "m":"Hệ thống đã tắt quyền chỉnh sửa nội dung này"})
            result = f(*args, **kwargs)
            return result
        return __checkEditable
    return _checkEditable



# -------------------------- MANAGER --------------------------------


@app.post("/api/login")
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


@app.get("/api/auto-login")
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
    newName = body.get("newName")
    password = body.get("password")

    updated = sqlExecute("UPDATE manager set FULL_NAME = %s where ACCOUNT = %s and PASSWORD = %s", [
        newName, account, password])

    if(updated != 0):
        return jsonify({"m": "Đổi tên thành công"})
    else:
        return jsonify({"e": True, "m": "Lỗi xảy ra, không có gì thay đổi"})




 

@app.get("/api/manager")
@jwt_required()
def getManager():
    managers = sqlExecute("SELECT `ID`, `ROOT`, `ACCOUNT`, `FULL_NAME` FROM `manager` WHERE 1",[],2)
    return jsonify(managers)


@app.post("/api/manager")
@jwt_required()
def addManager():
    reqAccount = get_jwt_identity()

    root = sqlExecute("SELECT * FROM `manager` WHERE ACCOUNT = %s AND ROOT = 1",[reqAccount],1)
    if(root == None):
        return jsonify({"e": True, "m": "Chỉ tài khoản Root mới có quyền thực hiện hành động này"})

    body = request.get_json()
    account = body.get('account')
    password = body.get("password")
    fullName = body.get("fullName")

    insert = sqlExecute("INSERT INTO `manager`(`ACCOUNT`, `PASSWORD`, `FULL_NAME`) VALUES (%s,%s,%s)",[account,password,fullName])

    if(insert != 0):
        return jsonify({"m": "Thêm tài khoản thành công"})
    else:
        return jsonify({"e": True, "m": "Lỗi xảy ra, không có gì thay đổi"})

@app.delete("/api/manager")
@jwt_required()
def deleteManager():
    reqAccount = get_jwt_identity()
    body = request.get_json()
    password = body.get("password")
    id = body.get("id")


    root = sqlExecute("SELECT * FROM `manager` WHERE ACCOUNT = %s AND PASSWORD = %s AND ROOT = 1",[reqAccount,password],1)
    if(root == None):
        return jsonify({"e": True, "m": "Chỉ tài khoản Root mới có quyền thực hiện hành động này"})

   
    delete = sqlExecute("DELETE FROM `manager` WHERE ID = %s",[id])

    if(delete != 0):
        return jsonify({"m": "Xóa tài khoản thành công"})
    else:
        return jsonify({"e": True, "m": "Lỗi xảy ra, không có gì thay đổi"})


@app.patch("/api/manager/change-root")
@jwt_required()
def updateRoot():
    reqAccount = get_jwt_identity()
    body = request.get_json()
    password = body.get("password")
    toId = body.get("toId")

    print(password)
    print(toId)

    root = sqlExecute("SELECT * FROM `manager` WHERE ACCOUNT = %s AND PASSWORD = %s AND ROOT = 1",[reqAccount,password],1)
    if(root == None):
        return jsonify({"e": True, "m": "Chỉ tài khoản Root mới có quyền thực hiện hành động này"})


    updated2 = sqlExecute("UPDATE `manager` SET `ROOT`=%s WHERE ID=%s",[0,root.get('ID')])
    updated = sqlExecute("UPDATE `manager` SET `ROOT`=%s WHERE ID=%s",[1,toId])
   
    if(updated != 0):
        return jsonify({"m": "Thay đổi quyền Root thành công"})
    else:
        return jsonify({"e": True, "m": "Lỗi xảy ra, không có gì thay đổi"})
# ------------------------------------    KHOA ----------------

@app.get("/api/manager/department")
@jwt_required()
def getDepartment():
    account = get_jwt_identity()
    departments = sqlExecute("SELECT * FROM `department` WHERE 1", [], 2)

    return jsonify(departments)

@app.post("/api/manager/department/insert")
@checkEditable("DEPARTMENT")
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
@checkEditable("DEPARTMENT")
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
            "UPDATE `department` set NAME = %s where ID = %s", [name, id])
        numberChange += changed

    if(sortName):
        changed = sqlExecute(
            "UPDATE `department` set SORT_NAME = %s where ID = %s", [sortName, id])
        numberChange += changed

    if(newId):
        changed = sqlExecute(
            "UPDATE `department` set ID = %s where ID = %s", [newId, id])
        numberChange += changed

    if(numberChange != 0):
        return jsonify({"m": "Có "+str(numberChange)+" thay đổi được cập nhật"})
    else:
        return jsonify({"e": True, "m": "Lỗi xảy ra, không có gì thay đổi"})


@app.post("/api/manager/department/delete")
@checkEditable("DEPARTMENT")
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
@checkEditable("MAJOR")
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
@checkEditable("MAJOR")
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
@checkEditable("MAJOR")
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
@checkEditable("CLASS")
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
@checkEditable("CLASS")
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
@checkEditable("CLASS")
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










#----------------------- GIÁO VIÊN CỐ VẤN -------------------------------------------------------

@app.get("/api/instructor")
@jwt_required()
def getInstructor():
    account = get_jwt_identity()
    body = request.get_json()

    result = sqlExecute("select * from instructor where 1",[],2)
    return jsonify(result)

@app.post("/api/instructor")
@checkEditable("INSTRUCTOR")
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
@checkEditable("INSTRUCTOR")
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
@checkEditable("INSTRUCTOR")
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






#------------------------------------------ SINH  VIÊN ------------------------------------
@app.get("/api/student")
@jwt_required()
def getStudent():
    account = get_jwt_identity()
    body = request.get_json()
    students = sqlExecute("select * from student where 1",[],2)
    return jsonify(students)

@app.post("/api/student")
@checkEditable("STUDENT")
@jwt_required()
def postStudent():
    account = get_jwt_identity()
    body = request.get_json()
    classMajor= body.get("classMajor")
    studentId = body.get("studentId")
    fullName = body.get("fullName")
    address = body.get("address")
    dateOfBirth = body.get("dateOfBirth")
    gender = body.get("gender")
    citizenId = body.get("citizenId")



    insert = sqlExecute("INSERT INTO `student`( \
        `CLASS`, `STUDENT_ID`, `FULL_NAME`, `ADDRESS`, `DATE_OF_BIRTH`, `GENDER`, `CITIZEN_ID`) \
        VALUES (%s,%s,%s,%s,%s,%s,%s)",[classMajor,studentId,fullName,address,dateOfBirth,gender,citizenId])

    if(insert):
         return jsonify({"m":"Thêm thành công"})

    return jsonify({"m":"Có lỗi xảy ra","e": True})

@app.put("/api/student")
@checkEditable("STUDENT")
@jwt_required()
def putStudent():
    account = get_jwt_identity()
    body = request.get_json()
    id = body.get("id")
    classMajor= body.get("classMajor")
    studentId = body.get("studentId")
    fullName = body.get("fullName")
    address = body.get("address")
    dateOfBirth = body.get("dateOfBirth")
    gender = body.get("gender")
    citizenId = body.get("citizenId")

    print("Class major")
    print(classMajor)

    update = sqlExecute("UPDATE `student` SET `CLASS`=%s, `STUDENT_ID`=%s,\
        `FULL_NAME`=%s,`ADDRESS`=%s,`DATE_OF_BIRTH`=%s,`GENDER`=%s,`CITIZEN_ID`=%s WHERE ID = %s",
        [classMajor,studentId,fullName,address,dateOfBirth,gender,citizenId,id])

    if(update):
         return jsonify({"m":"Thay đổi thành công"})

    return jsonify({"m":"Có lỗi xảy ra","e": True})

@app.delete("/api/student")
@checkEditable("STUDENT")
@jwt_required()
def deleteStudent():
    account = get_jwt_identity()
    body = request.get_json()
    password = body.get("password")
    id = body.get("id")


    user = sqlExecute(
        "SELECT * from manager where ACCOUNT = %s and PASSWORD = %s", [account, password], 1)

    if(user == None):
        return jsonify({"e": True, "m": "Xác nhận mật khẩu sai"})

    delete = sqlExecute("DELETE FROM `student` WHERE ID = %s",[id])
    if(delete):
         return jsonify({"m":"Xóa thành công"})

    return jsonify({"m":"Có lỗi xảy ra","e": True})


# ----------------------  QUYỀN CHỈNH SỬA ---------------------------

@app.get("/api/editable")
def getEditable():
    result = sqlExecute("select * from editable where 1",[],1)
    return result

@app.patch("/api/editable")
@jwt_required()
def patchEditable():
    account = get_jwt_identity()
    body = request.get_json()
    password = body.get('password')
    department = body.get('department')
    major = body.get('major')
    classMajor = body.get('class')
    instructor = body.get('instructor')
    student = body.get('student')

    user = sqlExecute("Select * from manager where ACCOUNT = %s and PASSWORD = %s and ROOT = 1",[account,password],1)
    if(user == None):
        return jsonify({"e":True, "m":"Bạn không có quyền quản lý hệ thống"})

    updated = 0

    if(department != None):
        update = sqlExecute("UPDATE editable SET DEPARTMENT = %s WHERE 1",[department])
        print(str(update))
        updated += update
    if(major != None):
        update = sqlExecute("UPDATE editable SET MAJOR = %s WHERE 1",[major])
        updated += update
    if(classMajor != None):
        update = sqlExecute("UPDATE editable SET CLASS = %s WHERE 1",[classMajor])
        updated += update
    if(instructor != None):
        update = sqlExecute("UPDATE editable SET INSTRUCTOR = %s WHERE 1",[instructor])
        updated += update
    if(student != None):
        update = sqlExecute("UPDATE editable SET STUDENT = %s WHERE 1",[student])
        updated += update

    if(updated != 0):
        return jsonify({"m":"Đã lưu thay đổi"})
    return jsonify({"e":True, "m":"Không có gì thay đổi"})



if __name__ == "__main__":
    if prod:
        app.run(port=80)
    else:
        app.run(debug=True)
