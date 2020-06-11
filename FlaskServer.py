import flask
from flask import Flask, request, send_file, Response, render_template, session, url_for, redirect
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO, join_room
import datetime
import sqlite3
import smtplib
import re
from json import dumps
from flask_cors import CORS
from chatterbot import ChatBot
from chatterbot.trainers import ListTrainer, ChatterBotCorpusTrainer
import os
from datetime import timedelta, datetime

# import spacy

# spacy.load('en')

app = Flask(__name__)
app.config['SECRET_KEY'] = "khg14545L5JK5454"
CORS(app)
cors = CORS(app, resources={r"/*": {"origins": "*"}})

socketio = SocketIO(app)


class AdministratorControl:
    def __init__(self):
        """this create databased if not exist and store user credentials and payment information"""
        self.connection = sqlite3.connect('BillPaymentCredentials.db')
        self.cursor = self.connection.cursor()
        self.cursor.execute(
            "CREATE TABLE IF NOT EXISTS credentials (email TEXT, password TEXT,firstname TEXT,lastname TEXT,"
            "homeaddress,phonenumber,time TEXT)")
        self.time = Time()

    def insert_creds(self, email, password, firstname, lastname, homeaddress, contact):
        """this will insert new user credentials into database
        it will first check to see if email exist in the database
        if so it will return false or true if it dose not exist
        a time stamp will also be inserted to keep track of when
        the user signed up"""
        if not self.check_if_email_exist(email):
            self.cursor.execute(
                "INSERT INTO credentials(email, password,firstname,lastname,homeaddress,phonenumber,time)VALUES(?,?,?,?,?,?,?)",
                (email, password, firstname, lastname, homeaddress, contact, str(self.time.date())))
            self.connection.commit()
            return True
        return False

    def check_if_email_exist(self, email):
        """This function is responsible for check to see of email already
        in the database and return tue it is else false if its not"""
        self.cursor.execute("SELECT email FROM credentials WHERE email = ?", (email,))
        username = self.cursor.fetchall()
        if username:
            for data in username[0]:
                if data == email:
                    return True
        return False

    def delete_all(self):
        """this will clean the entire database"""
        self.cursor.execute("DELETE FROM credentials")
        self.connection.commit()

    def getAllCreds(self):
        """this will get all credentials from database"""
        self.cursor.execute("SELECT * FROM credentials")
        creds = self.cursor.fetchall()
        if creds:
            return creds
        else:
            return "None"

    def get_password(self, email):
        """this function will retrieve the password corresponding to the user input email address
        and send a email to the user if as forget  password recovery"""
        self.cursor.execute("SELECT password FROM credentials WHERE email = ?", (email,))
        data = self.cursor.fetchall()
        if data:
            return data[0][0]
        return False

    def get_firstName(self, email):
        """this will get first name from database using the email address"""
        self.cursor.execute("SELECT firstname FROM credentials WHERE email = ?", (email,))
        data = self.cursor.fetchall()
        if data:
            return data[0][0]
        return ""

    def loginCheck(self, email, password):
        """this function will check if user credentials matches credentials in databes
        compare using the email address"""
        self.cursor.execute("SELECT password FROM credentials WHERE email = ?", (email,))
        data = self.cursor.fetchall()
        if data:
            for creds in data:
                if creds[0] == password:
                    return True
        return False

    def loginCheckReturnName(self, email, password):
        """this function will check if user credentials matches credentials in databes
        compare using the email address and will return the user name"""
        self.cursor.execute("SELECT password,firstname FROM credentials WHERE email = ?", (email,))
        data = self.cursor.fetchall()
        if data:
            for creds in data:
                if creds[0] == password:
                    return creds[1]
        return False

    class Payments:
        def __init__(self):
            self.connectionToPay = sqlite3.connect('MakePayment.db')
            self.cursorToPay = self.connectionToPay.cursor()
            self.cursorToPay.execute(
                "CREATE TABLE IF NOT EXISTS payments (time TEXT,amount TEXT,utilityname TEXT,utilityaccountnumber,status TEXT,"
                "email TEXT,bank TEXT,bankaccountNumber TEXT,otheroptions TEXT,creditcard TEXT,cvv_cvc TEXT)")
            self.time = Time()

        def insert(self, amount, utility, utilityaccountnumber, ID_email, bank, bankaccountNumber, Options_for_flow,
                   creditCard, cvv_cvc):
            self.cursorToPay.execute(
                "INSERT INTO payments(time,amount,utilityname,utilityaccountnumber,status,email,bank,bankaccountNumber,otheroptions,creditcard,cvv_cvc)VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (self.time.date(), amount, utility, utilityaccountnumber, "PENDING", ID_email, bank, bankaccountNumber,
                 Options_for_flow, creditCard, cvv_cvc))
            self.connectionToPay.commit()
            return True

        def get(self, Id, QTY=None):
            self.cursorToPay.execute(
                "SELECT time,amount,utilityname,status,bank,bankaccountNumber FROM payments WHERE email = ?", (Id,))
            data = self.cursorToPay.fetchall()
            if data:
                if QTY:
                    storeQtyAmount = []
                    for i, contents in enumerate(data):
                        if i != QTY:
                            storeQtyAmount.append(contents)
                        else:
                            return storeQtyAmount
                    return storeQtyAmount
                else:
                    return data
            else:
                return None

        def getPending(self):
            self.cursorToPay.execute("SELECT * from payments WHERE status = ?", ("PENDING",))
            data = self.cursorToPay.fetchall()
            if data:
                return data
            else:
                return None

        def getPaid(self):
            self.cursorToPay.execute("SELECT * from payments WHERE status = ?", ("PAID",))
            data = self.cursorToPay.fetchall()
            if data:
                return data
            else:
                return None

        def getAll(self):
            self.cursorToPay.execute("SELECT * from payments")
            data = self.cursorToPay.fetchall()
            if data:
                return data
            else:
                return None

        def getQuery(self, query="PENDING"):
            if query.lower() == "complete":
                query = "PAID"
            elif query.lower() == "pending":
                query = "PENDING"
            self.cursorToPay.execute("SELECT * FROM payments WHERE status = ?", (query,))
            data = self.cursorToPay.fetchall()
            if data:
                return data
            else:
                return None

        def updateAll(self):
            self.cursorToPay.execute("UPDATE payments SET status = 'PAID' WHERE status = 'PENDING'")
            self.connectionToPay.commit()

        def updateAsPaid(self, email, date, bank, utility, amount):
            self.cursorToPay.execute(
                "UPDATE status from payments WHERE status = 'PENDING' AND email = ? AND time = ? AND bank = ? AND utilityname = ? AND amount = ?",
                (email, date, bank, utility, amount))
            self.connectionToPay.commit()


class Email:
    def __init__(self):
        pass

    def send(self, sendTo, contents):
        """NOTE...this will allow less secure app to communicate ... https://myaccount.google.com/lesssecureapps?pli=1
        if its not activated then emails will not be sent"""
        print(sendTo)
        try:
            subject = "Password Restore"
            server = smtplib.SMTP('smtp.gmail.com', 587)  # or prot 465 or 587
            admin = 'areset0000@gmail.com'
            passw = 'meloneyblair1'
            msg = MIMEMultipart()
            msg['From'] = admin
            msg['To'] = sendTo
            msg['Subject'] = subject
            body = str(contents)
            msg.attach(MIMEText(body, 'plain'))
            text = msg.as_string()
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(admin, passw)
            server.sendmail(admin, sendTo, text)
            server.close()
            print("send email to :" + sendTo)
            return True
        except Exception as e:
            print(e)
            return False

    def validate(self, email):
        """this will check to see if email is in correct format"""
        is_valid = re.search(r'[\w.-]+@[\w.-]+.\w+', email)
        if is_valid:
            return True
        return False

    def sendValidate(self, email, msg):
        if self.validate(email):
            if self.send(email, msg):
                return True
        return False


def reversTupleInList(value):
    storeReversItem = []
    valueLength = len(value)
    for i in range(valueLength):
        storeReversItem.append(value[valueLength - i - 1])
    return storeReversItem


def queryState(value="Pending"):
    states = ["Pending", "Complete", "Other"]
    stateShuffle = []
    for i, shuffle in enumerate(states):
        if i == 0:
            stateShuffle.append(value)
        if shuffle != value:
            stateShuffle.append(shuffle)
    return stateShuffle


def affiliates(asString=False, asArray=False, getBanks=False, getBusiness=False):
    banks = ["Bank of Nova Scotia", "First-Caribbean international", "Co-operative Bank",
             "RBTT Bank Grenada", "Republic Bank Grenada"]
    bussines = ["Grenlec", "NAWASA", "Flow"]
    # nameOfBanks = bussines + "`" + banks
    if asString:
        bank_stingBuilder = ""
        business_stringBuilder = ""
        for bank in banks:
            bank_stingBuilder = bank_stingBuilder + bank + ","
        for buss in bussines:
            business_stringBuilder = business_stringBuilder + buss + ","
        combind = business_stringBuilder + "`" + bank_stingBuilder
        return combind
    elif asArray:
        combind = []
        combind.append(bussines)
        combind.append(banks)
        return combind
    elif getBanks:
        return banks
    elif getBusiness:
        return bussines
    return None


class Bot:
    def __init__(self):
        self.bot = ChatBot('kai')
        self.time = Time()

    def botTrainer(self):
        trainer = ChatterBotCorpusTrainer(self.bot)
        trainer.train("chatterbot.corpus.english")

    def respond(self, question):
        file_date = ('what is the date today')
        file_date1 = ('what date is it')
        file_date2 = ('what is the date')

        file_time = ('what is the time')
        file_time1 = ('what time is it')

        file_day = ('what is the day today')
        file_day1 = ('what day is it')
        file_day2 = ('what is the day')

        file_year = ('what is the year today')
        file_year1 = ('what year is it')
        file_year2 = ('what is the year')

        date_time = str(self.time.date())
        time_t = str(self.time.time())
        day = str(self.time.day())
        year = str(self.time.year())

        message = question

        if message == file_date or message == file_date1 or message == file_date2:
            return "the date is " + date_time
        elif message == file_time or message == file_time1:
            return "the time is " + time_t
        elif message == file_day or message == file_day1 or message == file_day2:
            return "today is the " + day
        elif message == file_year or message == file_year1 or message == file_year2:
            return "the year is " + year
        else:
            replay = self.bot.get_response(message)
            return replay


class Time:
    def __init__(self):
        """this class is responsible for generating time from the internet"""

    def month(self):
        return datetime.now().month

    def day(self):
        return datetime.now().day

    def year(self):
        return datetime.now().year

    def time(self):
        times = datetime.today() - timedelta(hours=4, minutes=0)
        tempstrip = ''
        for time in str(times.time()):
            if time == ".":
                break
            else:
                tempstrip = tempstrip + time
        times = datetime.today().strptime(tempstrip, "%H:%M:%S")
        return times.strftime("%I:%M:%S")

    def date(self):
        return str(self.month()) + "/" + str(self.day()) + "/" + str(self.year())


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        f = request.files['file']
        f.save(secure_filename(f.filename))
        return 'file uploaded successfully'
    templete = """<form action = "" method = "POST" 
         enctype = "multipart/form-data">
         <input type = "file" name = "file" />
         <input type = "submit"/>
        </form>"""
    return templete


@app.route('/download', methods=['GET', 'POST'])
def download():
    """this will make app available for download"""
    path = r"billPayApp.apk"
    return send_file(path, as_attachment=True, cache_timeout=0)


@app.route('/banks')
def bankNames():
    """this will return all the name of the banks we are working with
    and the business we service"""
    return affiliates(asString=True)


@app.route('/sign_up')
def register():
    """this route will be call when the user wants to sign up with the app"""
    register_user = AdministratorControl()
    try:
        email, password, firstName, lastName, homeAdress, contact = request.args.get("register").split(" ")
        homeAdress = homeAdress.replace("~", " ")
        if register_user.insert_creds(email, password, firstName, lastName, homeAdress, contact):
            return "true"
        else:
            return "false"
    except:
        return "error"


@app.route('/recover_password')
def forgetPassword():
    """this route will be call when the user wants to recover password"""
    billPayDb = AdministratorControl()
    recoverEmail = Email()

    email = request.args.get("recover")
    if recoverEmail.validate(email):
        password = billPayDb.get_password(email)
        if password:
            if recoverEmail.send(email, "the password for you bill pay account is: " + str(password)):
                return "true"
        else:
            return "false"
    else:
        return "error"


@app.route('/login')
def login():
    """this route will be call when the user wants to login to the app"""
    billPayDb = AdministratorControl()
    validateEmail = Email()
    try:
        email, password = request.args.get("login").split(" ")
        if validateEmail.validate(email):
            if billPayDb.loginCheck(email, password):
                return "true"
            else:
                return "false"
        else:
            return "error"
    except:
        return "error"


@app.route('/pay')
def pay():
    """this route will be call when the user wants to make a payment"""
    billPay = AdministratorControl().Payments()
    amount, utilityName, utilityAccountNumber, email, bankName, bankAccountNumber, otherOptions_for_flow, creditCardNumer, cvv_cvc_number = request.args.get(
        "pay").split(";")
    if billPay.insert(amount, utilityName, utilityAccountNumber, email, bankName, bankAccountNumber, creditCardNumer,
                      otherOptions_for_flow, cvv_cvc_number):
        return "true"
    return "false"


@app.route('/notification')
def paymentInfo():
    """this route will be call when the user wants to make a payment"""
    billPay = AdministratorControl().Payments()
    userId = request.args.get("info")
    statusInfo = billPay.get(userId)
    if statusInfo:
        return str(reversTupleInList(statusInfo)).replace("[", "").replace("]", "").replace("'", "").replace(",",
                                                                                                             "").replace(
            "(", "").replace(") ", ",").replace(")", ",")
    else:
        return "No Records..."


@app.route('/testing', methods=["GET"])
def testing():
    print("testing")
    return Response(dumps([{
        "userId": 1,
        "id": 1,
        "title": "sunt aut facere repellat provident occaecati excepturi optio reprehenderit",
        "body": "quia et suscipit\nsuscipit recusandae consequuntur expedita et cum"
    }, {
        "userId": 1,
        "id": 2,
        "title": "sunt fhgfdhgfh",
        "body": "quia et suscipit\nsuscipit recusandae consequuntur expedita et cum"
    }
    ]), mimetype="text/json")


@app.route('/pending', methods=["GET", "POST"])
def getPendingData():
    get = AdministratorControl().Payments()
    try:
        if get:
            return str(get.getPending())
        else:
            return "No Records"
    except:
        return "Error"


@app.route('/paid', methods=["GET", "POST"])
@app.route('/complet', methods=["GET", "POST"])
def getCompletedData():
    get = AdministratorControl().Payments()
    try:
        if get:
            print(get.getPaid())
            return str(get.getPaid())
        else:
            return "No Records"
    except:
        return "Errors"


@app.route('/get/all', methods=["GET", "POST"])
@app.route('/get_all', methods=["GET", "POST"])
def getAllData():
    get = AdministratorControl().Payments()
    try:
        if get:
            return str(get.getAll())
        else:
            return "No Records"
    except:
        return "Errors"


@app.route('/update', methods=["POST"])
def updateSelecedPayments():
    if request.method == "POST":
        DB = AdministratorControl().Payments()
        selecedItems = request.form.get('selected-items')
        items = []
        arrayOfItems = []
        if selecedItems:
            for tuple_item in selecedItems.split('+++'):
                for i in tuple_item.split(','):
                    if not i.isdigit():
                        if i != None or i != []:
                            items.append(str(i).replace("'", "").replace("(", "").replace(")", ""))
                if items:
                    arrayOfItems.append(tuple(items))
                items.clear()
        if arrayOfItems:
            for item in arrayOfItems:
                DB.updateAsPaid(item[5].lstrip(" "), item[0].lstrip(" "), item[6].lstrip(" "), item[2].lstrip(" "),
                                item[1].lstrip(" "))
            return render_template("billPayProProgram.html", data=DB.getQuery(), state=queryState())
    return "", 204


@app.route('/update/all', methods=["POST"])
def updateAllPayments():
    if request.method == "POST":
        payemntDb = AdministratorControl().Payments()
        selectAllItems = request.form.get('select-all-items')
        if selectAllItems == 'true':
            payemntDb.updateAll()
    return "", 204


@app.route('/getallcreds', methods=["GET", "POST"])
def getAllCreds():
    """this will get all credentials from database"""
    creds = AdministratorControl().getAllCreds()
    if creds:
        return str(creds)
    else:
        return "None"


@app.route('/policy', methods=["GET", "POST"])
def policy():
    return render_template("policiesAndInfo.html")


@app.route('/submission/process', methods=["GET", "POST"])
def submissionProcess():
    respondChecks = "Complete,Other,Pending"
    response = request.form.get(
        "submissionForm")  # this is a hidden button value that returns the value of a spesific elemnnt
    messages = request.form.get(
        "submissionMessages")  # this will return the value of the query state eg: pending, completed..
    if request.method == "POST":
        for checks in response.strip(" "):  # for email address
            if checks == "@":
                DB = AdministratorControl().Payments()
                send_email = Email()
                send_email.sendValidate(response, DB.getQuery(messages))
                break
        else:
            if response == "print":  # to sent to printer or fax machine
                print(response)
            elif response:  # for option menu drop down
                if response in respondChecks:
                    DB = AdministratorControl().Payments()
                    query_data = DB.getQuery(response)
                    if query_data:
                        return render_template("billPayProProgram.html", data=query_data, state=queryState(response))
                    return render_template("billPayProProgram.html", data=None, state=queryState(response))
    return "", 204


@app.route('/billPayPro', methods=["GET", "POST"])
def billPayPro():
    if request.method == "POST":
        username = request.form.get("pro_username")
        password = request.form.get("pro_password")
        if username == "billpay" and password == "billpay":
            DB = AdministratorControl().Payments()
            query_data = DB.getQuery()
            if query_data:
                return render_template("billPayProProgram.html", data=query_data, state=queryState())
            return render_template("billPayProProgram.html", data=None, state=queryState())
        else:
            errorMsg = "Incorrect username or password"
            return render_template("billPayProLogin.html", errorMsg=errorMsg)
    return render_template("billPayProLogin.html")


@app.route('/online/billpayment', methods=["GET", "POST"])
def onlinePay():
    DB = AdministratorControl()
    PAY = DB.Payments()
    qty = 10
    greatings = "Hello "
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        bankname = request.form.get("bank-name")
        bankaccountnumber = request.form.get("bank-account-number")
        utilityaccountnumber = request.form.get("account-number")
        otherOptions_for_flow = request.form.get("flow-option")
        amount = request.form.get("amount")
        utilityname = request.form.get("utility-name")
        if username and password:
            user = DB.loginCheckReturnName(username, password)
            if user:
                session['visits'] = username
                return render_template("onlinePayments.html", billHistory=PAY.get(username, qty), credsCheck="true",
                                       customerName=greatings + str(user).title(), affiliates=affiliates(asArray=True),
                                       creds=None, stayInRegisterScreen=False, stayInPaymentScreen=False, isSent=None)
            return render_template("onlinePayments.html", billHistory=None, customerName=greatings,
                                   affiliates=affiliates(), creds=False, stayInRegisterScreen=False,
                                   stayInPaymentScreen=False, isSent=None)
        if bankname and bankaccountnumber and utilityaccountnumber and amount and utilityname:
            visiterUsername = session['visits'] = session.get('visits')
            DB.Payments().insert(amount, utilityname, utilityaccountnumber, visiterUsername, bankname,
                                 utilityaccountnumber, otherOptions_for_flow, "None", "None")
            return render_template("onlinePayments.html", billHistory=PAY.get(visiterUsername, qty),
                                   customerName=greatings, affiliates=affiliates(asArray=True), creds=None,
                                   stayInRegisterScreen=False, stayInPaymentScreen=True, isSent=True)
    if 'visits' in session:
        visiterUsername = session['visits'] = session.get('visits')
        user = DB.get_firstName(visiterUsername)
        return render_template("onlinePayments.html", billHistory=PAY.get(visiterUsername, qty), credsCheck="true",
                               customerName=greatings + str(user).title(), affiliates=affiliates(asArray=True),
                               creds=None, stayInRegisterScreen=False, stayInPaymentScreen=False, isSent=None)
    return render_template("onlinePayments.html", billHistory=None, customerName=greatings, affiliates=affiliates(),
                           creds=None, stayInRegisterScreen=False, stayInPaymentScreen=False, isSent=None)


@app.route('/online/register', methods=["GET", "POST"])
def onlineRegister():
    if request.method == "POST":
        greatings = "Hello "
        register_user = AdministratorControl()
        firstname = request.form.get("first-name")
        lastname = request.form.get("last-name")
        email = request.form.get("email")
        address = request.form.get("address")
        password = request.form.get("password")
        contact = request.form.get("phone-number")
        if register_user.insert_creds(email, password, firstname, lastname, address, contact):
            session['visits'] = email
            return render_template("onlinePayments.html", credsCheck="true", customerName=greatings + firstname.title(),
                                   affiliates=affiliates(asArray=True), creds=None, stayInRegisterScreen=False,
                                   stayInPaymentScreen=False, isSent=None)
        return render_template("onlinePayments.html", credsCheck="true", customerName=greatings + firstname.title(),
                               affiliates=affiliates(asArray=True), creds=None, stayInRegisterScreen=True,
                               stayInPaymentScreen=False, isSent=None)
    return "", 204


@app.route('/close/session')
def closeSession():
    session.pop('visits', None)
    return redirect(url_for('onlinePay'))


@app.route('/chat/bot')
def chatBot():
    return render_template("chatbot.html")


@socketio.on('send_message')
def handle_send_message_event(data):
    bot = Bot()
    response = str(bot.respond(data['message']))
    socketio.emit('receive_message', {"username": "kai: ", 'message': response}, room=data['room'])


@socketio.on('join_room')
def handle_join_room_event(data):
    join_room(data["room"])
    socketio.emit('join_room-announcement', {"username": "kai: ", "message": "Hello how can I help"}, room=data['room'])


@app.route('/notificaton/update/disconnect/passdue', methods=["GET", "POST"])
def notification():
    """this function will get request for customer to receive notifications
    once its check then they will receive notification on disconnect and pastdue and more"""
    if request.method == "POST":
        disconnect = request.form.get("disconnect")
        pass_due = request.form.get("pass-due")
        print(disconnect, pass_due)
    return "", 204


@app.route('/recover/password', methods=["POST"])
def recoverPassword():
    if request.method == "POST":
        DB = AdministratorControl()
        email = Email()
        recover_email = request.form.get("password-recovery")
        password = DB.get_password(recover_email)
        email.sendValidate(recover_email, "Your password for your BillPay account is: " + password)
    return "", 204


if __name__ == "__main__":
    socketio.run(app, debug=True, host="192.168.0.4", port=os.environ.get("PORT",80))
    '''while True:
        try:
            # app.run(debug=True,host="192.168.1.116",port=22012)
            socketio.run(app, debug=True, host="192.168.1.116", port=22012)
        except Exception as error:
            print(error)'''





