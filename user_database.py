import pymongo
from pymongo import MongoClient
import os
import datetime
import pandas as pd
import json
import time
import math
import requests

user = os.environ.get("DB_USER")
secret = os.environ.get("DB_PASS")
cluster = pymongo.MongoClient(f"mongodb://localhost:27017")
db = cluster["data"]
memberdata = db["localdata"]
vehicledata = db["vehicle"]
allinonedata = db["aio"]



# --------------------------------
# ---------- memberdata ----------
# --------------------------------
def add_user(user):
    return memberdata.insert_one(user)
def check_for_user(username):
    if memberdata.find_one({"username" : username}):
        return True
    else:
        return False
def getRole(username):
    user = memberdata.find_one({"username": username})
    if user:
        return user.get("role")
    else:
        return None
def getStatus(username):
    user = memberdata.find_one({"username" : username})
    if user:
        return user.get("status")
    else:
        return None
def getUsername(username):
    user = memberdata.find_one({"username" : username})
    if user:
        return user.get("username")
    else:
        return None
def getVehicle(username):
    user = memberdata.find_one({"username": username})
    if user and (user.get("role") == "teacher" or user.get("role") == "admin"):
        veh = []
        vehicles = vehicledata.find({})
        for vehicle in vehicles:
            veh.append(vehicle["vehicle_plate"])
        return veh
    else:
        return None
def createTeacher(username, password, role, vehicle):
    if role == "teacher":
        userelement = {
            "role" : "teacher",
            "username" : username,
            "password" : password,
            "manage" : vehicle
        }
        memberdata.insert_one(userelement)
def createStudent(display,username, password, role, cls):
    if role == "student":
        userelement = {
            "display" : display,
            "role" : "student",
            "username" : username,
            "password" : password,
            "class" : cls,
            "status" : "",
            "telephone" : "",
            "checkbox" : False
        }
        memberdata.insert_one(userelement)
def updateStatus(username, new_status):
    result = memberdata.update_one(
        {"username": username},
        {"$set": {"status": new_status}}
    )
    return result.modified_count > 0
def getClass(cls, subcls):
    merge = f"{cls}-{subcls}"
    data = memberdata.find({"class" : merge})
    return data
def delete_by_role(role):
    find_all = memberdata.find({})
    for element in find_all:
        try:
            if element["role"] == role:
                memberdata.delete_one(element)
        except:
            pass
def get_manage_vehicle(username):
    data = memberdata.find_one({"username" : str(username)})
    if data:
        return data.get("manage")
    return None
def addStudent(file):
    try:
        data = pd.read_excel(file)
        DataStore = {}
        count = 0
        filename = file.filename.rsplit(".", 1)[0]
        for i in data["Unnamed: 1"]:
            count += 1
            if str(i) != "nan" and str(i) != "เลขที่":
                DataStore[data["Unnamed: 4"][count-1]] = [str(i), data["Unnamed: 7"][count-1]]

        with open(f"class_list/{filename}.json", "w+") as json_file:
            json_file.write(json.dumps(DataStore))
        with open(f"class_list/{filename}.json", "r") as f:
            data = json.load(f)
        for i in data:
            unique_num = i
            no = data[i][0]
            name = data[i][1]
            createStudent(display=name, username=unique_num, password=no, role="student", cls=filename)
        return True
    except Exception as e:
        print(f"Error in addStudent function: {str(e)}")
        return False
def add_manage(username, vehicle):
    data = memberdata.find_one({"username" : str(username)})
    if data:
        filter_query = {"username": username}
        new_values = {
            '$set': {
                'manage': vehicle
            }
        }
        result = memberdata.update_one(filter_query, new_values)
        if result.modified_count > 0:
            print("Document updated successfully.")
        else:
            print("No document was updated.")
def get_name_from_number(number):
    print(f"get_name_from_number : {number}")
    data = memberdata.find_one({"password" : str(number)})
    if data:
        return data.get("username")
    return None
def get_name_from_display(display):
    data = memberdata.find_one({"display" : str(display)})
    print(data)
    if data:
        return data.get("username")
    return None
def get_number_from_name(id: str):
    data = memberdata.find_one({"username" : str(id)})
    if data:
        return data.get("password")
    return None
def get_display_from_name(id):
    data = memberdata.find_one({"username" : str(id)})
    if data:
        return data.get("display")
    return None
def get_class_from_name(id):
    data = memberdata.find_one({"username" : str(id)})
    if data:
        return data.get('class').replace('-','/')
    return None
def get_username_from_name_and_class(password, class_name):
        query = {
            'password': password,
            'class': class_name
        }
        document = memberdata.find_one(query, {'_id': 0, 'username': 1})
        if document:
            return document['username']
        else:
            return "No matching document found"
def getTeacher():
    try:        
        cursor = memberdata.find({"role": "teacher"})
        teachers = list(cursor)
        for teacher in teachers:
            teacher['_id'] = str(teacher['_id'])  # Convert ObjectId to string if needed
        return teachers
    except Exception as e:
        print(f"An error occurred: {e}")
        return []
def getStudents():
    try:        
        cursor = memberdata.find({"role": "student"})
        students = list(cursor)
        for student in students:
            student['_id'] = str(student['_id'])  # Convert ObjectId to string if needed
        return students
    except Exception as e:
        print(f"An error occurred: {e}")
        return []
def get_all_students_name():
    users = getStudents()
    store = {}
    for i in users:
        store[i['password']] = [i['display'], i['username']]
    return store
def updatePhone(username, new_status):
    result = memberdata.update_one(
        {"username": username},
        {"$set": {"telephone": new_status}}
    )
    return result.modified_count > 0
def getPhone(id):
    data = memberdata.find_one({"username" : str(id)})
    if data:
        return data.get("telephone")
    return None

# ---------------------------------
# ---------- vehicledata ----------
# ---------------------------------
def getVehiclePlate(username):
    query = {"members": username}
    vehicle_plate = vehicledata.find_one(query, {"vehicle_plate": 1})
    if vehicle_plate:
        return vehicle_plate.get("vehicle_plate")
    else:
        return None
def createVehicle(vehicle_plate, line_token_students, line_token_parents):
    userelement = {
        "vehicle_plate": vehicle_plate,
        "image" : "",
        "members": [],
        "up" : [],
        "down" : [],
        "lat" : "",
        "lng" : "",
        "last_updated_by" : "",
        'token_students' : line_token_students,
        'token_parents' : line_token_parents,
        'timestamp' : 0
        }
    vehicledata.insert_one(userelement)
def duplicate(username):
    cursor = vehicledata.find()
    for document in cursor:
        if username in document["members"]:
            return True
    return False
def add_members_to_vehicle(vehicle_plate, new_members):
    for name in new_members:
        if not duplicate(name):
            query = {"vehicle_plate": vehicle_plate}
            result = vehicledata.update_one(query, {"$push": {"members": name}})
            vehicledata.update_one(query, {"$push": {"up": name}})
            if result.modified_count > 0:
                print(f"Members added to vehicle {vehicle_plate} successfully.")
            else:
                print(f"No documents were updated. Vehicle {vehicle_plate} not found.")
        else:
            print("Duplicate")
    return True
def check_for_vehicle(vehicle_plate):
    if vehicledata.find_one({"vehicle_plate" : vehicle_plate}):
        return True
    else:
        return False
def getMembers(vehicle_plate):
    if check_for_vehicle(vehicle_plate):
        vehicle = vehicledata.find_one({"vehicle_plate" : vehicle_plate})
        return vehicle.get("members"), vehicle.get('up'), vehicle.get('down')
    return None
def get_up_list(vehicle_plate):
    document = vehicledata.find_one({"vehicle_plate": vehicle_plate})
    if document:
        up_list = document.get('up', [])
        print(f"'up' list for vehicle {vehicle_plate}: {up_list}")
        return up_list
    else:
        print(f"No document found for vehicle {vehicle_plate}.")
        return None
def get_down_list(vehicle_plate):
    document = vehicledata.find_one({"vehicle_plate": vehicle_plate})
    if document:
        up_list = document.get('down', [])
        print(f"'down' list for vehicle {vehicle_plate}: {up_list}")
        return up_list
    else:
        print(f"No document found for vehicle {vehicle_plate}.")
        return None
def move_up_to_down(vehicle_plate, element):
    up_list = get_up_list(vehicle_plate)
    if up_list and element in up_list:
        filter_criteria = {"vehicle_plate": vehicle_plate}
        update_query = {
            "$pull": {"up": element}, 
            "$addToSet": {"down": element} 
        }
        result = vehicledata.update_one(filter_criteria, update_query)
        
        if result.modified_count > 0:
            print(f"Element {element} moved from 'up' to 'down' for vehicle {vehicle_plate}.")
            return True
        else:
            print(f"No documents were updated for vehicle {vehicle_plate}.")
            return False
    else:
        print(f"Element {element} is not present in the 'up' list for vehicle {vehicle_plate}.")
        return False
def move_down_to_up(vehicle_plate, element):
    down_list = get_down_list(vehicle_plate)
    if down_list and element in down_list:
        filter_criteria = {"vehicle_plate": vehicle_plate}
        update_query = {
            "$pull": {"down": element},
            "$push": {"up": element}
        }
        result = vehicledata.update_one(filter_criteria, update_query)
        if result.modified_count > 0:
            print(f"Element {element} moved from 'down' to 'up' for vehicle {vehicle_plate}.")
            return True
        else:
            print(f"No documents were updated. Vehicle {vehicle_plate} not found.")
            return False
def isMembers(vehicle_plate, element):
    try:
        find_one = vehicledata.find_one({"vehicle_plate" : vehicle_plate})
        if element in find_one.get("members"):
            return True
        else:
            return False
    except:
        return False
def get_status_from_vehicle(vehicle_plate, username):
    find_one = vehicledata.find_one({"vehicle_plate": vehicle_plate})
    if find_one:
        if username in find_one.get("up", []):
            return "up"
        elif username in find_one.get("down", []):
            return "down"
        elif username in find_one.get("members", []):
            return "members"
        else:
            return "not_found"
    else:
        return "not_found"
def updateImg(vehicle_plate, data):
    new_image_filename = data 
    find_one = vehicledata.find_one({"vehicle_plate": vehicle_plate})
    if find_one:
        vehicledata.update_one({"vehicle_plate": vehicle_plate}, {"$set": {"image": new_image_filename}})
        return True
    else:
        print(f"Vehicle {vehicle_plate} not found.")
        return False
def update_timestamp(vehicle_plate, timestamp_unix: int):
    find_one = vehicledata.find_one({"vehicle_plate": vehicle_plate})
    if find_one:
        vehicledata.update_one({"vehicle_plate": vehicle_plate}, {"$set": {"timestamp": timestamp_unix}})
        return True
    else:
        print(f"Vehicle {vehicle_plate} not found.")
        return False
def get_image_path(vehicle_plate):
    find_one = vehicledata.find_one({"vehicle_plate": vehicle_plate})
    if find_one:
        return find_one.get("image")
    return ""
def deleteVehicle(vehicle_plate):
    find_one = vehicledata.find_one({"vehicle_plate": vehicle_plate})
    if find_one:
        vehicledata.delete_one({"vehicle_plate": vehicle_plate})
        return True
    return False
def getVehicleDetail(vehicle_plate):
    if check_for_vehicle(vehicle_plate):
        vehicle = vehicledata.find_one({"vehicle_plate" : vehicle_plate})
        return vehicle.get("vehicle_plate"), vehicle.get("members"), vehicle.get('up'), vehicle.get('down'), vehicle.get("image")
    return None
def updateLatLng(vehicle_plate, username, new_lat, new_lng):
    print(vehicle_plate, username, new_lat, new_lng)
    if check_for_vehicle(vehicle_plate):
        filter_query = {"vehicle_plate": vehicle_plate}
        new_values = {
            '$set': {
                'lat': new_lat,
                'lng': new_lng,
                'last_updated_by': username  
            }
        }
        result = vehicledata.update_one(filter_query, new_values)
        if result.modified_count > 0:
            print("Document updated successfully.")
        else:
            print("No document was updated.")
    else:
        print("Vehicle not found.")
def getLatLng(vehicle_plate):
    if check_for_vehicle(vehicle_plate):
        data = vehicledata.find_one({"vehicle_plate" : vehicle_plate})
        lat = data['lat']; lng = data['lng']
        return (lat,lng)
def getLineToken(vehicle_plate, which_one):
    if check_for_vehicle(vehicle_plate):
        data = vehicledata.find_one({"vehicle_plate" : vehicle_plate})
        print(f'data : {data}')
        token = data[which_one]
        return token
def get_down_from_vehicle_send_line(plate):
    if check_for_vehicle(plate[0]):
        data = vehicledata.find_one({"vehicle_plate": plate[0]})
        down_members = data.get('down', [])
        members = {}
        for i in down_members:
            members[i] = []
            members[i].append((get_display_from_name(i)))
            members[i].append(get_number_from_name(i))
            members[i].append(get_class_from_name(i))
        if down_members:
            start_content = "นักเรียนที่ยังไม่ขึ้นรถ ::"
            sum = start_content
            for i in members:
                sum += f"\n{members[i][0]} เลขที่ : {members[i][1]} ชั้น : {members[i][2]}"
            #print(sum)
            lineSent(sum, plate, 'token_students')
        else:
            lineSent("นักเรียนขึ้นรถบัสครบจำนวนทุกคนแล้วครับ", plate, 'token_students')
        return members
    else:
        return []
def get_down_from_vehicle_send_line_specific_car(plate):
    if check_for_vehicle(plate[0]):
        data = vehicledata.find_one({"vehicle_plate": plate[0]})
        down_members = data.get('down', [])
        members = {}
        for i in down_members:
            members[i] = []
            members[i].append((get_display_from_name(i)))
            members[i].append(get_number_from_name(i))
            members[i].append(get_class_from_name(i))
        if down_members:
            start_content = f"แจ้งเตือนรถ {plate[0]}\nนักเรียนที่ยังไม่ขึ้นรถ ::"
            sum = start_content
            for i in members:
                sum += f"\n{members[i][0]} เลขที่ : {members[i][1]} ชั้น : {members[i][2]}"
            #print(sum)
            lineSent(sum, plate, 'token_students')
        else:
            lineSent(f"แจ้งเตือนรถ {plate[0]}\nนักเรียนขึ้นรถบัสครบจำนวนทุกคนแล้วครับ", plate, 'token_students')
        return members
    else:
        return []
def get_all_vehicle():
    data = vehicledata.find({}, {'vehicle_plate': 1, '_id': 0})
    return data
def get_timestamp(vehicle_plate):
    if check_for_vehicle(vehicle_plate):
        data = vehicledata.find_one({"vehicle_plate" : vehicle_plate})
        timestamp = data['timestamp']
        return timestamp
    else:
        return None
def calculate_timestamp(timestampdict: dict):
    store = {}
    for i,v in timestampdict.items():
        current_timestamp = int(time.time()) 
        checker = (int(v) == current_timestamp)
        store[i] = checker
    return store
def get_all_timestamp():
    store = {}
    plate = vehicledata.find({}, {'vehicle_plate': 1, '_id': 0})
    for documents in plate:
        store[documents['vehicle_plate']] = get_timestamp(documents['vehicle_plate'])
    return store
def get_up_down_from_vehicle(vehicle_plate):
    store = {}
    if not check_for_vehicle(vehicle_plate):
        return None
    data = vehicledata.find_one({"vehicle_plate": vehicle_plate})
    if not data:
        return {}
    for member_id in data.get('members', []):
        number = get_number_from_name(member_id)
        status = 'ขึ้นรถ' if member_id in data.get('up', []) else 'ลงรถ'
        phone = getPhone(str(member_id))
        store[number] = {
            str(get_display_from_name(member_id)): [status, phone, member_id]
        }
    return store


# --------------------------------
# --------- allinonedata ---------
# --------------------------------
def check_for_vehicle_aio(vehicle_plate):
    if allinonedata.find_one({"vehicle_plate" : vehicle_plate}):
        return True
    else:
        return False
def createVehicle_aio(vehicle_plate):
    data = getVehicleDetail(vehicle_plate)
    userelement = {
        "vehicle_plate": vehicle_plate,
        "image" : data[4],
        "members": data[1],
        "up" : data[2],
        "down" : data[3],
        "seat" : []
        }
    allinonedata.insert_one(userelement)
def getVehicleDetail_aio(vehicle_plate):
    if check_for_vehicle(vehicle_plate):
        vehicle = allinonedata.find_one({"vehicle_plate" : vehicle_plate})
        return vehicle.get("vehicle_plate"), vehicle.get("members"), vehicle.get('up'), vehicle.get('down'), vehicle.get("image"), vehicle.get("seat")
    return None
def getMembers_aio(vehicle_plate):
    if check_for_vehicle(vehicle_plate):
        vehicle = allinonedata.find_one({"vehicle_plate" : vehicle_plate})
        return vehicle.get("members"), vehicle.get('up'), vehicle.get('down'), vehicle.get('seat')
    return None
def addSpecificData(vehicle_plate, key, value):
    if check_for_vehicle_aio(vehicle_plate):
        filter = {"vehicle_plate": vehicle_plate}
        new_seat_entry = {key: value}
        update = {"$push": {"seat": new_seat_entry}}
        allinonedata.update_one(filter, update)
        query = {"vehicle_plate": vehicle_plate}
        result = allinonedata.update_one(query, {"$push": {"up": key}})
        return True
    else:
        return False
def getKeyfromValue(vehicle_plate, val):
    if check_for_vehicle_aio(vehicle_plate):
        vehicle = allinonedata.find_one({"vehicle_plate": vehicle_plate})
        seat_data = vehicle.get('seat')
        result = find_key(val, seat_data)
        return result
    else:
        return None
def getMembersViaKeyAIO(username):
    if check_for_user(username):
        datastore = memberdata.find_one({"username" : username})
        return datastore.get('display')
    else:
        return None
def move_up_to_down_aio(vehicle_plate, seat):
    filter_criteria = {"vehicle_plate": vehicle_plate, f"up.{seat}": {"$exists": True}}
    update_query = {
        "$unset": {f"up.{seat}": ""},
        "$set": {f"down.{seat}": f"$up.{seat}"}
    }
    result = allinonedata.update_one(filter_criteria, update_query)
    if result.modified_count > 0:
        print(f"Element at seat {seat} moved from 'up' to 'down' for vehicle {vehicle_plate}.")
        return True
    else:
        print(f"No documents were updated. Vehicle {vehicle_plate} not found or seat {seat} not in 'up' array.")
        return False



# --------------------------------
# -------- extra modules ---------
# --------------------------------
def get_route_distance_ors(start_coords, end_coords, mode='driving-car'):
    headers = {
        'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8',
    }
    call = requests.get(f'https://api.openrouteservice.org/v2/directions/driving-car?api_key=5b3ce3597851110001cf6248cfcc4ae77f384640a52cda1f7f0c71cf&start={str(start_coords[0])},{str(start_coords[1])}&end={str(end_coords[0])},{str(end_coords[1])}', headers=headers)

    if call.status_code == 200:
        data = call.json()
        return (data['features'][0]['properties']['segments'][0]['distance'])
    else:
        print("Request failed with status code", call.status_code)
    return None
def lineSent(message, vehicle_plate, which_one):
    token = getLineToken(vehicle_plate[0], which_one)
    # Line variables
    print(f'token : {token}')
    url = 'https://notify-api.line.me/api/notify'
    headers = {'content-type':'application/x-www-form-urlencoded','Authorization':'Bearer '+ token}
    r = requests.post(url, headers=headers, data = {'message':message})
    return r.text

#Need to be fix
def move_down_to_up_aios(vehicle_plate, element):
    filter_criteria = {"vehicle_plate": vehicle_plate}
    update_query = {
        "$pull": {"up": element},
        "$push": {"down": element}
    }
    result = allinonedata.update_one(filter_criteria, update_query)
    if result.modified_count > 0:
        print(f"Element {element} moved from 'up' to 'down' for vehicle {vehicle_plate}.")
        return True
    else:
        print(f"No documents were updated. Vehicle {vehicle_plate} not found or element not in 'up'.")
        return False
def move_down_to_ups(vehicle_plate, element):
    filter_criteria = {"vehicle_plate": vehicle_plate}
    update_query = {
        "$pull": {"down": element},
        "$push": {"up": element}
    }
    result = allinonedata.update_one(filter_criteria, update_query)
    if result.modified_count > 0:
        print(f"Element {element} moved from 'down' to 'up' for vehicle {vehicle_plate}.")
        return True
    else:
        print(f"No documents were updated. Vehicle {vehicle_plate} not found or element not in 'down'.")
        return False



# --------------------------------
# ------------- etc. -------------
# --------------------------------
def filters(members, up, down):
    unknown_members = [i for i in members if (i not in up) and (i not in down)]
    return unknown_members
def find_key(input_value, data):
    for d in data:
        for key, value in d.items():
            if key == input_value:
                return value
    return None