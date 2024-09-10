from flask import Flask, jsonify, request, render_template, redirect, flash, url_for, session
from passlib.hash import pbkdf2_sha256
import uuid
import user_database as db
import datetime
import requests


class User:
    def signup(self):
        mydate = datetime.datetime.now()
        timenow = (mydate.strftime("%X"))
        user = {
            "_id": uuid.uuid4().hex,
            "username": request.form.get('username'),
            "password": request.form.get('password'),
        }
        if db.check_for_user(user["username"]):
            return False
        else:
            db.add_user(user)
            return True
    def login(self):
        user_exists = db.check_for_user(request.form.get('username'))
        username = db.check_for_user(request.form.get('username'))
        real_password = db.get_number_from_name(request.form.get('username'))
        password = request.form.get('password')
        if user_exists:
            if password == real_password:
                session['username'] = request.form.get('username')
                return True
            else:
                return False
        else:
            return False
    def logout(self):
        if 'username' in session:
            session.pop('username')
            return True
        else:
            return False
    def addTeacher(self):
        user_exists = db.check_for_user(request.form.get("username"))
        if not user_exists:
            username = request.form.get("username")
            password = request.form.get("password")
            vehicle = request.form.get('vehicle')
            db.createTeacher(username=username, password=password, role="teacher", vehicle=vehicle)
            return True
    def addVehicle(self):
        user_exists = db.check_for_user(request.form.get("vehicle-name"))
        manage_plr = request.form.get('vehicle-select')
        line_token_students = request.form.get('line-token-students')
        line_token_parents = request.form.get('line-token-parents')
        if not user_exists:
            vehicle_name = request.form.get("vehicle-name")
            db.createVehicle(vehicle_name, line_token_students, line_token_parents)
            db.add_manage(manage_plr, vehicle_name)
            return True
    def sendCustomText(self, vehicle):
        message = request.form.get('vehicle-name')
        db.lineSent(message, [vehicle], 'token_students')
        