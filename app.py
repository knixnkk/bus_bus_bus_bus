from flask import Flask, render_template, request, redirect, flash, url_for, session, jsonify, session, Response, send_from_directory
from user.models import User
import os
import user_database as db
import socket
from werkzeug.utils import secure_filename
import json
from serial import Serial
from pynmeagps import NMEAReader
import logging
import cv2
import face_recognition
import pickle
import requests
import time
from pygrabber.dshow_graph import FilterGraph
import math
from sklearn import neighbors
from face_recognition.face_recognition_cli import image_files_in_folder


camfDown_url = "http://" + socket.gethostbyname(socket.gethostname()) + ":5000/camfDown"
camfUp_url = "http://" + socket.gethostbyname(socket.gethostname()) + ":5000/camfUP"

def list_camera_devices():
    graph = FilterGraph()
    return graph.get_input_devices()


# Load KNN classifier
try:
    with open("classifier/trained_knn_model.clf", 'rb') as f:
        knn_clf = pickle.load(f)
except:
    print("CANT FIND MODEL PLEASE TRAIN FACE RECOGNITION BEFORE START")
    pass

def predict(img, knn_clf, threshold=0.4):
    face_box = face_recognition.face_locations(img)
    if len(face_box) == 0:
        return []
    faces_encodings = face_recognition.face_encodings(img, known_face_locations=face_box)
    closest_distances = knn_clf.kneighbors(faces_encodings, n_neighbors=2)
    matches = [closest_distances[0][i][0] <= threshold for i in range(len(face_box))]
    return [(pred, loc) if rec else ("unknown", loc) for pred, loc, rec in zip(knn_clf.predict(faces_encodings), face_box, matches)]

def generate_frames(camera_index):
    webcam = cv2.VideoCapture(camera_index)
    try:
        while True:
            rval, frame = webcam.read()
            if not rval:
                continue
            
            frame = cv2.flip(frame, 1)
            frame_copy = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            frame_copy = cv2.cvtColor(frame_copy, cv2.COLOR_BGR2RGB)
            
            predictions = predict(frame_copy, knn_clf)
            font = cv2.FONT_HERSHEY_DUPLEX
            
            for name, (top, right, bottom, left) in predictions:
                top *= 4
                right *= 4
                bottom *= 4
                left *= 4
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 255), 2)
                cv2.putText(frame, name, (left-10, top-6), font, 0.8, (255, 255, 255), 1)
            if predictions and predictions[0][0] != "unknown":
                print(predictions[0][0])
                try:
                    if camera_index == 0:
                        requests.post(camfDown_url, data=predictions[0][0])
                    elif camera_index == 1:
                        requests.post(camfUp_url, data=predictions[0][0])
                except requests.RequestException as e:
                    print(f"Request failed: {e}")
            
            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                continue
            frame = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    finally:
        webcam.release()
        
app = Flask(__name__)
app.config['STATIC_FOLDER'] = 'static'

UPLOAD_FOLDER = 'uploads/'
FRAMES_FOLDER = 'frames/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['FRAMES_FOLDER'] = FRAMES_FOLDER

ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

#8aeRrnO0G1KD9SVFAMSR8Oh28Fie1M41GvioF6uZM2i
#9EpRy8ZyXOvE7mdJJc7D6g4J0RRQhHfOg7TxRi2sw8W
@app.route('/')
def first():
    if 'username' not in session:
        return render_template('signin.html')

    user_exists = db.check_for_user(session['username'])

    if not user_exists:
        return render_template('signin.html')
    else:
        role = db.getRole(session['username'])

        if role is None:
            return render_template('error.html', error_message="Role not found for the user.")

        if role == "student":
            try:
                getVehiclePlate = db.getVehiclePlate(session["username"])
                getDisplay = db.get_display_from_name(session["username"])
                getUsername = db.getUsername(session["username"])
                stat = db.get_status_from_vehicle(getVehiclePlate, getUsername)
            except Exception as e:
                return render_template('error.html', error_message=str(e))

            return render_template('index-student.html', VehiclePlate=getVehiclePlate, status=stat, display=getDisplay, username=getUsername, image_path = db.get_image_path(getVehiclePlate))

        elif role == 'teacher':
            getVehiclePlate = db.getVehicle(session["username"])
            vehicleDict = {str(i + 1): value for i, value in enumerate(getVehiclePlate)}
            teachers = db.getTeacher()
            plates = [document['vehicle_plate'] for document in db.get_all_vehicle()]
            teacher = []
            for i in teachers:
                teacher.append(i['username'])
            #print(vehicleDict)
            return render_template('index-teacher.html', data=vehicleDict, options=teacher, vehicle_options=plates)

        elif role == 'admin':
            try:
                options = db.getVehicle(session['username'])
                data = db.get_all_students_name()
            except Exception as e:
                return jsonify(error_message=str(e))

            return render_template('index-admin.html', options=options, data=data)

        else:
            return render_template('error.html', error_message="Invalid role")


### Student AJAX
@app.route('/updateIMGPATH', methods=["POST"])
def updateIMGPATH():
    data = request.get_json()
    IMG_PATH = db.get_image_path(data['vehicle_plate'])
    return jsonify(img='images/' + IMG_PATH)
@app.route('/updateVehiclePlate', methods=["GET"])
def updateVehiclePlate():
    getVehiclePlate = db.getVehiclePlate(session["username"])
    return jsonify(data=getVehiclePlate)
@app.route('/updateStatusAJAX', methods=["GET"])
def updateStatusAJAX():
    getVehiclePlate = db.getVehiclePlate(session["username"])
    getUsername = db.getUsername(session["username"])
    stat = db.get_status_from_vehicle(getVehiclePlate, getUsername)
    return jsonify(data=stat)



@app.route('/signin', methods = ['POST', 'GET'])
def signin():
    if(request.method == 'POST'):
        user = User()
        success_flag = user.login()
        if(success_flag):
            return redirect('/')
        else:
            return redirect('/')


@app.route('/setting', methods=['GET', 'POST'])
def setting():
    role = db.getRole(session['username'])
    if role == "teacher":
        options = db.getVehicle(session['username'])
        l_data = {}
        if request.method == 'POST':
            l_data = {}
            #print("Called")
            plate = request.form.get("vehicle-select")
            cls = request.form.get("class")
            subclass = request.form.get("subclass")
            #print(f"cls : {cls}")
            #print(f"subcls : {subclass}")
            #print(f"plate : {plate}")
            data = db.getClass(cls, subclass)
            for i in data:
                l_data[i['password']] = [i['display'], i['checkbox'], i['username']]
            return render_template('setting.html', options=options, data=l_data, merge=f"{cls}-{subclass}", class_hidden=f"{cls}-{subclass}", plate_hidden=plate)
        
        return render_template('setting.html', options=options, data=l_data)
    else:
        return redirect('/')

@app.route('/sendchb', methods=['POST'])
def sendchb():
    if request.method == 'POST':
        selected_checkboxes = []

        for key in request.form:
            if key.startswith('status_checkbox_') and request.form[key] == 'on':
                checkbox_number = key.replace('status_checkbox_', '')
                selected_checkboxes.append(checkbox_number)

        plate_hidden = request.form.get('plate-hidden')
        class_hidden = request.form.get('class-hidden')

        #print(f'Selected checkboxes: {selected_checkboxes}')
        new_member = []
        for i in selected_checkboxes:
            print(f"user : {i}")
            new_member.append(i.split('_')[1])
        if new_member:
            db.add_members_to_vehicle(plate_hidden, new_member)
        #print(f'Plate hidden value: {plate_hidden}')
        #print(f'Class hidden value: {class_hidden}')
    return redirect('/setting')

     
     
@app.route('/addTeacher', methods=["POST"])
def addTeacher():
    if(request.method == "POST"):
        user = User()
        user.addTeacher()
        return redirect('/')

@app.route('/addVehicle', methods=["POST"])
def addVehicle():
    if(request.method == "POST"):
        user = User()
        user.addVehicle()
        return redirect('/')


@app.route('/upload_students', methods=['POST'])
def upload_students():
    if request.method == "POST":
        if 'fileUpload' not in request.files:
            return "No file part"

        file = request.files['fileUpload']

        if not file:
            return "No selected file"

        filename = secure_filename(file.filename)

        allowed_extensions = {'csv', 'xlsx', 'xls'}
        if '.' not in filename or filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
            return "Invalid file format"

        try:
            db.addStudent(file)

            return redirect('/')
        except Exception as e:
            return f"Error processing file: {str(e)} \n Contact Admin !!!"
@app.route('/selectVehicle', methods=["POST"])
def selectVehicle():
    if request.method == "POST":
        getVehiclePlate = db.getVehicle(session["username"])
        vehicleDict = {str(i + 1): value for i, value in enumerate(getVehiclePlate)}
        vehicle_plate = vehicleDict[request.form.get("selectVehicleNumber")]
        data = db.getMembers(vehicle_plate=vehicle_plate)
        #print(f"members : {len(data[0])} ; up : {len(data[1])} ; down : {len(data[2])}")
        return render_template('teacher-label.html', main_content=vehicle_plate, up=str(len(data[1])), down=str(len(data[2])), unknow=str((len(data[0])-len(data[1]) - len(data[2]))), image_path = db.get_image_path(vehicle_plate))
    return redirect('/')

@app.route('/linkVehicle', methods=["POST"])
def linkVehicle():
    try:
        if request.method == "POST":
            # Retrieve vehicle data
            getVehiclePlate = db.getVehicle(session["username"])
            vehicleDict = {str(i + 1): value for i, value in enumerate(getVehiclePlate)}
            vehicle_plate_number = request.form.get("selectVehicleNumber")
            vehicle_plate = vehicleDict.get(vehicle_plate_number)

            if not vehicle_plate:
                # Return a 400 error if vehicle_plate is not found
                return jsonify({'error': 'Invalid vehicle plate number'}), 400

            # Fetch data related to the vehicle
            data = db.getMembers(vehicle_plate=vehicle_plate)
            
            # Return JSON with the URL to redirect to
            return jsonify({
                'redirect': url_for('teacher_label', vehicle_plate=vehicle_plate),
                'data': {
                    'main_content': vehicle_plate,
                    'up': str(len(data[1])),
                    'down': str(len(data[2])),
                    'unknow': str(len(data[0]) - len(data[1]) - len(data[2])),
                    'image_path': db.get_image_path(vehicle_plate)
                }
            })
        return redirect('/')
    except Exception as e:
        # Log the exception
        logging.error(f"Error in selectVehicle route: {e}")
        # Return a 500 error with a generic message
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/teacher-label/<vehicle_plate>')
def teacher_label(vehicle_plate):
    # Fetch the necessary data
    data = db.getMembers(vehicle_plate=vehicle_plate)
    return render_template(
        'teacher-label.html',
        main_content=vehicle_plate,
        up=str(len(data[1])),
        down=str(len(data[2])),
        unknow=str(len(data[0]) - len(data[1]) - len(data[2])),
        image_path=db.get_image_path(vehicle_plate)
    )

@app.route('/LabelUpdateMembers', methods=["POST"])
def labelUpdateMembers():
    vehicle_plate = request.form.get('vehicle_plate')
    if not vehicle_plate:
        return jsonify({'error': 'vehicle_plate is required'}), 400
    try:
        data = db.getMembers(vehicle_plate=vehicle_plate)
        if not data:
            return jsonify({'error': 'No data found for the provided vehicle_plate'}), 404
        response = {
            'UP': len(data[1]), 
            'DOWN': len(data[2]),
            'IMG_PATH': 'images/' + db.get_image_path(vehicle_plate)
        }
        return jsonify(response)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
                   
@app.route('/check_student', methods=["GET"])
def checkStudent():
    if request.method == "GET":
        getVehiclePlate = db.getVehicle(session["username"])
        #print("getVehiclePlate : ", getVehiclePlate)
        print(getVehiclePlate)
        db.get_down_from_vehicle_send_line(getVehiclePlate)
        return redirect('/')
@app.route('/list/<item>', methods=["GET"])
def listpeople(item):
    if request.method == "GET":
        print(db.get_up_down_from_vehicle(item))
        return render_template('teacher-table.html',fortable=db.get_up_down_from_vehicle(item))
@app.route('/tableUpdate', methods=["POST"])
def tableUpdate():
    data = request.get_json()
    return jsonify(data=db.get_up_down_from_vehicle(data['vehicle_plate']))
@app.route('/up/<item>')
def up(item):
    vehicleplate, username = item.split('-')
    print(vehicleplate, username)
    db.move_down_to_up(str(vehicleplate), str(username))
    return redirect('/')

@app.route('/down/<item>')
def down(item):
    vehicleplate, username = item.split('-')
    db.move_up_to_down(vehicleplate, username)
    return redirect('/')

@app.route('/logout')
def logout():
    if session:
        session.clear()
    return redirect('/')
@app.route('/upload', methods=['POST'])
def upload():
    if 'imageUpload' in request.files:
        file = request.files['imageUpload']
        #print(file)
        selected_vehicle = request.form.get("vehicle-select")
        if selected_vehicle and file.filename != '':
            upload_directory = 'static/images/'
            new_filename = secure_filename(selected_vehicle+"."+file.filename.split('.')[-1])
            file.save(os.path.join(upload_directory, new_filename))
            db.updateImg(selected_vehicle, new_filename)

            return redirect('/') 

    return 'File upload failed.'
@app.route('/deleteVehicle', methods=['POST'])
def deleteVehicle():
    if session:
        selected_vehicle = request.form.get("deleteVehicleSelect")
        db.deleteVehicle(selected_vehicle)

        return redirect('/') 

    return 'failed.'

@app.route('/deleteRole', methods=["POST"])
def deleteRole():
    if session:
        role = request.form.get("roleSelect")
        db.delete_by_role(role)
        return redirect('/')
    return redirect('/')



# --------------------------------
# ------------- AIO. -------------
# --------------------------------

## IMPORTANT NEED TO BE FIX!!!!!!!!!!!!




@app.route('/all-in-one', methods=["POST", "GET"])
def all_in_one():
    Manage_Vehicle = db.get_manage_vehicle(session['username'])
    if not db.check_for_vehicle_aio(Manage_Vehicle):
        db.createVehicle_aio(Manage_Vehicle)

    members = db.getMembers(Manage_Vehicle)
    mykeys = db.getMembers_aio(Manage_Vehicle)[3]
    parsing_keys = {k for d in mykeys for k in d.keys()}
    parsing_keys_json = json.dumps(list(parsing_keys)) if parsing_keys else '[]'
    #print(parsing_keys)
    #print(parsing_keys_json)
    return render_template('all-in-one.html', vecname=Manage_Vehicle, members=members[0], parsing_keys_json=parsing_keys_json)

@app.route('/addAIO', methods=["POST"])
def addAIO():
    if request.method == 'POST':
        data = request.json
        if data is None:
            return jsonify({"message": "Error: No JSON data received"}), 400

        selected_member = data.get('student-select')
        label_content = data.get('username')
        vehicle_plate_data = data.get('vehiclePlate')
        #print(vehicle_plate_data)
        #print("Selected member:", selected_member)
        #print("Label content:", label_content.replace("Seat ID: ", ""))
        # Add data to seat
        if db.addSpecificData(vehicle_plate_data, label_content.replace("Seat ID: ", ""), selected_member):
            return jsonify({"message": "Data received successfully"}), 200
        else:
            return jsonify({"message": "Failed"}), 500
@app.route('/get_session_data')
def get_session_data():
    return jsonify(session_data=session.get('username'))
@app.route('/get_seat', methods=["POST"])
def get_seat():
    #print(request.get_json())
    payload = request.get_json()
    seat = payload['seat']  # Adjusted to 'seat'

    data = db.getKeyfromValue(vehicle_plate="DEF 456", val=seat)  # Adjusted to 'seat'
    returndata = db.getMembersViaKeyAIO(data)
    
    return returndata
@app.route('/aio_up', methods=["POST"])
def aio_up():
    data = request.get_json()
    #print(data)
    db.move_down_to_up_aios(data['plate'], data['seat'])
    return redirect('/all-in-one')
@app.route('/aio_down', methods=["POST"])
def aio_down():
    data = request.get_json()
    db.move_up_to_down_aio(data['plate'], data['seat'])
    return redirect('/all-in-one')

@app.route('/updateStatusAIO', methods=["POST"])
def updateStatusAIO():
    return redirect('/all-in-one')


# --------------------------------

@app.route('/camfUP', methods=['POST'])
def camfrogUP():
    data = request.get_data()
    split_data = data.decode('utf-8').split('-')
    classes = f"{split_data[0]}-{split_data[1]}"
    number = f"{split_data[2]}"
    name = db.get_username_from_name_and_class(password=number, class_name=classes)
    vehicleplate = db.getVehiclePlate(name)
    #print(name, type(name), vehicleplate, type(vehicleplate))
    db.move_down_to_up(vehicleplate, name)
    return data

@app.route('/camfDown', methods=['POST'])
def camfrogDown():
    data = request.get_data()
    split_data = data.decode('utf-8').split('-')
    classes = f"{split_data[0]}-{split_data[1]}"
    number = f"{split_data[2]}"
    name = db.get_username_from_name_and_class(password=number, class_name=classes)
    vehicleplate = db.getVehiclePlate(name)
    #print(name, type(name), vehicleplate, type(vehicleplate))
    db.move_up_to_down(vehicleplate, name)
    return data

GPS_SENT = False
@app.route('/maps')
def maps():
    if session:
        role = db.getRole(session['username'])
        if role == "teacher":
            return render_template('gpstest.html')
    return redirect('/')

@app.route('/coords', methods=['POST'])
def receive_coords():
    print(f'request.get_json() : {request.get_json()}')
    if session:
        role = db.getRole(session['username'])
        if role == "teacher":
            try:
                data = request.get_json()
                if not data:
                    return jsonify({"error": "Invalid data"}), 400
                print("Received coordinates:", data)
                global GPS_SENT
                GPS_SENT = False
                print(f"db.get_manage_vehicle(session['username']) : {db.get_manage_vehicle(str(session['username']))}")
                db.updateLatLng(db.get_manage_vehicle(session['username']), session['username'], data['latitude'], data['longitude'])
                return jsonify(state=True)
            except Exception as e:
                return jsonify({"error": str(e)}), 500
    return redirect('/')
@app.route('/messageAPI/<item>', methods=["POST"])
def messageAPI(item):
    if(request.method == "POST"):
        user = User()
        user.sendCustomText(vehicle=item)
        return redirect('/')


#### Make function like ajax #######
@app.route('/check_d', methods=['GET'])
def check_d():
    try:
        global GPS_SENT
        vehicle_location = db.getLatLng(db.get_manage_vehicle(session['username']))
        print(f'Vehicle location data: {vehicle_location}')
        getVehiclePlate = db.get_manage_vehicle(session["username"])
        start_coords = ["104.7794201", "17.402847"]  # [longitude, latitude]
        end_coords = [vehicle_location[1], vehicle_location[0]]
        
        distance = db.get_route_distance_ors(start_coords, end_coords)
        average_speed_kmh = 70
        speed_mps = average_speed_kmh * (1000 / 3600)  # Convert km/h to m/s
        travel_seconds = distance / speed_mps
        
        hours = int(travel_seconds // 3600)
        minutes = int((travel_seconds % 3600) // 60)
        remaining_seconds = int(travel_seconds % 60)
        
        message = (
            f"Another {str(hours)} hours and {str(minutes)} minutes and {str(remaining_seconds)} seconds to Destination"
        )
        if ((hours == 0) and (minutes < 30)) and (not GPS_SENT):
            GPS_SENT = True
            return jsonify(state=True, vehicle_plate=getVehiclePlate)
        return jsonify(state=False, vehicle_plate=getVehiclePlate)
    except:
        return jsonify(state=False)

@app.route('/d_indistance', methods=["POST"])
def d_indistance():
    getVehiclePlate = request.get_json()
    message = (
        f"The car will arrive at its destination in 30 minutes"
    )
    db.lineSent(message=message, vehicle_plate=[getVehiclePlate], which_one="token_parents")
    return redirect('/')



"""
with Serial('COM4', 9600, timeout=3) as stream:
        while stream:
            try:
                nmr = NMEAReader(stream)
                raw_data, parsed_data = nmr.read()
                if parsed_data is not None:
                    data = db.getLatLng(db.get_manage_vehicle(session['username']))
                    start_coords = [parsed_data.lon, parsed_data.lat]  # [longitude, latitude]
                    end_coords = [data[0], data[1]]
                    distance = db.get_route_distance_ors(start_coords, end_coords)
                    seconds = distance/(70*(5/18))
                    hours = seconds // 3600
                    minutes = (seconds // 60) - (hours * 60)
                    remaining_seconds = seconds % 60
                    if int(minutes) == 30  or int(minutes) == 10 or int(minutes) == 5:
                        db.lineSent(message=f"another {int(hours)} hours and {int(minutes)} minutes and {round(remaining_seconds)} seconds to Piyamaharachalai School")
                    return (int(minutes), round(remaining_seconds))
            except:
                pass
    """



@app.route('/timer', methods=["POST"])
def timer():
    data = request.get_data() # --> this is what time to count down in seconds like 1s, 5s, 15s, 30s, 60s, ...
    # make a function that can countdown while in a background or in another page but this countdown still run until time is up then use db.lineSent to send time is up
    return data

@app.route('/face_recog')
def face_recog():
    camDex = list_camera_devices()
    return render_template('face_recognition.html', camera_index=camDex)

@app.route('/video_feed')
def video_feed():
    # Get the camera index from query parameters
    camera_index =  request.args.get('camera', 0)
    camera_index = int(camera_index)  # Ensure it's an integer

    return Response(generate_frames(camera_index), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/settimerwithcalculation', methods=['POST'])
def set_timer_with_calculation():
    getVehiclePlate = db.getVehiclePlate(session["username"])
    print(f'Username : {session["username"]}')
    minutes = request.form.get('minutes')
    seconds = request.form.get('seconds')
    plate = request.form.get("vehicle-select")

    minutes = int(minutes)
    seconds = int(seconds)
    current_timestamp = int(time.time())
    # Perform calculations or actions with the timer values
    # For example, you might save these values or use them to set a timer
    calcTimer = (minutes*60) + seconds
    timestampwithTimer = current_timestamp+calcTimer
    db.update_timestamp(vehicle_plate=plate, timestamp_unix=timestampwithTimer)
    return redirect('/')

@app.route('/timestamp')
def get_timestamp():
    current_timestamp = int(time.time()) 
    all_timestamp_store = db.get_all_timestamp()
    ctimestamp = db.calculate_timestamp(all_timestamp_store)
    for i,v in ctimestamp.items():
        if v:
            print(i,v , type(i), type(v))
            db.get_down_from_vehicle_send_line_specific_car([i])
            return jsonify(state=v)
    return jsonify(state=False)

@app.route('/users')
def get_stundent():
    return jsonify(students=db.get_up_down_from_vehicle('khonkhaen'))

@app.route('/EditPhone', methods=["POST"])
def edit_phone():
    student_name = request.form.get('student_name')
    phone_number = request.form.get('phone_number')
    db.updatePhone(student_name, phone_number)
    return redirect('/')

@app.route('/getPhone', methods=["POST"])
def getPhone():
    receive_data = request.get_json()
    data = db.getPhone(receive_data)
    return jsonify(data=data)

@app.route('/AddFace', methods=["POST"])
def addFace():
    if 'fileUpload' not in request.files:
        return "No file part", 400

    file = request.files['fileUpload']
    
    if file.filename == '':
        return "No selected file", 400
    student_number = request.form.get('student_name')
    folder_name = f"{str(db.get_class_from_name(student_number)).replace('/','-')}-{db.get_number_from_name(student_number)}"
    print(folder_name)
    if file and allowed_file(file.filename):
        filename = file.filename
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Extract frames from the video
        extract_frames(file_path, filename,folder_name , fps=24)
        
        return redirect('/')
    else:
        return "Invalid file type", 400
def extract_frames(video_path, filename,folder_name, fps=24):
    if not os.path.exists(app.config['FRAMES_FOLDER']):
        os.makedirs(app.config['FRAMES_FOLDER'])
    if not os.path.exists(f"{app.config['FRAMES_FOLDER']}/{folder_name}"):
        os.makedirs(f"{app.config['FRAMES_FOLDER']}/{folder_name}")
    cap = cv2.VideoCapture(video_path)
    video_fps = cap.get(cv2.CAP_PROP_FPS)
    frame_interval = int(video_fps / fps)
    
    frame_count = 0
    while True:
        # Skip frames
        for _ in range(frame_interval):
            ret = cap.grab()
            if not ret:
                break
        
        # Read the frame
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_filename = os.path.join(f"{app.config['FRAMES_FOLDER']}/{folder_name}", f'{filename}_frame_{frame_count:04d}.png')
        cv2.imwrite(frame_filename, frame)
        frame_count += 1
    
    cap.release()
@app.route('/frames/<filename>')
def get_frame(filename):
    return send_from_directory(app.config['FRAMES_FOLDER'], filename)

def image_files_in_folder(folder):
    # Assuming this function returns a list of image file paths
    return [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

def train(train_dir, model_save_path, n_neighbors=2, knn_algo='ball_tree', verbose=False):
    X = []
    y = []
    for class_dir in os.listdir(train_dir):
        class_path = os.path.join(train_dir, class_dir)
        if not os.path.isdir(class_path):
            continue
        for img_path in image_files_in_folder(class_path):
            try:
                image = face_recognition.load_image_file(img_path)
                face_bounding_boxes = face_recognition.face_locations(image)
                print(f"Processing: {img_path}")
                if len(face_bounding_boxes) != 1:
                    if verbose:
                        print(f"Image {img_path} not suitable for training: {'Didnt find a face' if len(face_bounding_boxes) < 1 else 'Found more than one face'}")
                    continue
                X.append(face_recognition.face_encodings(image, known_face_locations=face_bounding_boxes)[0])
                y.append(class_dir)
            except Exception as e:
                print(f"Error processing image {img_path}: {e}")

    if not X:
        raise ValueError("No suitable images found for training.")
    
    if n_neighbors is None:
        n_neighbors = int(round(math.sqrt(len(X))))
        if verbose:
            print("Chose n_neighbors automatically:", n_neighbors)
    
    knn_clf = neighbors.KNeighborsClassifier(n_neighbors=n_neighbors, algorithm=knn_algo, weights='distance')
    knn_clf.fit(X, y)
    
    if model_save_path is not None:
        with open(model_save_path, 'wb') as f:
            pickle.dump(knn_clf, f)
        print("Training complete")
    
    return knn_clf

@app.route('/train_face_recog', methods=['GET'])
def train_face_recog():
    try:
        img_dir = "frames/"
        model_dir = "classifier/trained_knn_model.clf"
        if not os.path.isdir(img_dir):
            return jsonify({"error": "Image directory does not exist"}), 400
        
        train(img_dir, model_dir)
        return redirect('/')
    except Exception as e:
        print(f"Training failed: {e}")
        return jsonify({"error": str(e)}), 500
if __name__ == "__main__":
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    if not os.path.exists(FRAMES_FOLDER):
        os.makedirs(FRAMES_FOLDER)
    app.secret_key="anystringhere"
    app.config['SESSION_TYPE'] = 'filesystem'
    app.run(host=socket.gethostbyname(socket.gethostname()),debug=True)
