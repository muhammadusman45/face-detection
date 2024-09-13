from flask import Flask, request, jsonify
from flask_restx import Api, Resource
import face_recognition
import os
from PIL import Image
import io
import numpy as np
from flask_cors import CORS
app = Flask(__name__)
CORS(app) 
api = Api(app, doc='/docs')
ns = api.namespace('hello', description='Hello World operations')

ATTENDANCE_DIR = 'attendance_records'
os.makedirs(ATTENDANCE_DIR, exist_ok=True)

# Directory for storing uploaded images
IMAGE_DIR = 'uploaded_images'
os.makedirs(IMAGE_DIR, exist_ok=True)  
# List of known face encodings and names
known_face_encodings = []
known_face_names = []

# def load_known_faces():
#     known_faces = {
#         'usman': 'images/usman.png',
#         'john': 'images/usman-2.png',  # Add more face images here
#     }
    
#     for name, file_path in known_faces.items():
#         image = face_recognition.load_image_file(file_path)
#         face_encoding = face_recognition.face_encodings(image)[0]  # Get face encoding
#         known_face_encodings.append(face_encoding)
#         known_face_names.append(name)        
def load_known_faces():
    # Directory containing images of known faces
    known_faces_dir = 'uploaded_images'

    # Loop over all image files in the directory
    for filename in os.listdir(known_faces_dir):
        if filename.endswith('.png') or filename.endswith('.jpg') or filename.endswith('.jpeg'):
            file_path = os.path.join(known_faces_dir, filename)
            
            # Load the image and get the face encoding
            image = face_recognition.load_image_file(file_path)
            face_encodings = face_recognition.face_encodings(image)
            
            if face_encodings:  # Ensure that a face encoding was found
                face_encoding = face_encodings[0]  # Get the first encoding (assumes one face per image)
                
                # Use the file name (without extension) as the person's name
                name = os.path.splitext(filename)[0]
                
                # Append the encoding and name to the lists
                known_face_encodings.append(face_encoding)
                known_face_names.append(name)
            else:
                print(f"No face found in {file_path}")
def save_attendance(name):
    with open(os.path.join(ATTENDANCE_DIR, f"{name}.txt"), 'a') as file:
        file.write(f"{name} attended\n")

@ns.route('/')
class HelloWorld(Resource):
    def get(self):
        """Returns a Hello, World! message"""
        return {'message': 'Hello, World!'}

    def post(self):
        """Receives text and echoes it back"""
        data = request.get_json()
        if 'text' in data:
            return {'received_text': data['text']}
        else:
            return {'error': 'No text provided'}, 400

@app.route('/upload', methods=['POST'])
def image_upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
       
    # print("files ----->" , request.files['file'].filesname)
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    # Open and convert the image to RGB
    image = Image.open(io.BytesIO(file.read()))
    image = image.convert('RGB')  # Convert to RGB mode
    image_np = np.array(image)
    
    # Find faces in the uploaded image
    face_locations = face_recognition.face_locations(image_np)
    face_encodings = face_recognition.face_encodings(image_np, face_locations)
    print("image ----->" , face_encodings)
    tolerance = 0.5
    for face_encoding in face_encodings:
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding , tolerance=tolerance)
        face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
        name = "Unknown"
        print(matches)
        if True in matches:
            first_match_index = matches.index(True)
            name = known_face_names[first_match_index]
        
            save_attendance(name)
            message = f"Attendance recorded for {name}"
        else:
            message = "No known face matched, attendance not recorded"
    
    return jsonify({'status': message}), 200

@app.route('/upload-image', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # Save the uploaded image to the directory
    image_path = os.path.join(IMAGE_DIR, file.filename)
    file.save(image_path)

    return jsonify({'message': 'Image uploaded successfully!', 'image_path': image_path}), 200

if __name__ == '__main__':
    load_known_faces()  # Load known faces when starting the server
    app.run(debug=True)
