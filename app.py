from flask import Flask, request, jsonify
from flask_restx import Api, Resource
import face_recognition
import os
from PIL import Image
import io
import numpy as np
from flask_cors import CORS
import boto3
import time
from dotenv import load_dotenv
from pprint import pprint
from concurrent.futures import ThreadPoolExecutor
load_dotenv()

app = Flask(__name__)
CORS(app) 
api = Api(app, doc='/docs')
ns = api.namespace('hello', description='Hello World operations')

ATTENDANCE_DIR = 'attendance_records'
os.makedirs(ATTENDANCE_DIR, exist_ok=True)

IMAGE_DIR = 'uploaded_images'
os.makedirs(IMAGE_DIR, exist_ok=True)  
known_face_encodings = []
known_face_names = []

MINIO_URL=os.getenv('MINIO_URL', '')
MINIO_ACCESS_KEY=os.getenv('MINIO_ACCESS_KEY', '')
MINIO_SECRET_ACCESS_KEY=os.getenv('MINIO_SECRET_ACCESS_KEY', '')
MINIO_REGION=os.getenv('MINIO_REGION', '')
MINIO_BUCKET=os.getenv('MINIO_BUCKET', '')

minio_client = boto3.client(
    's3',
    endpoint_url=MINIO_URL,
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_ACCESS_KEY,
    region_name=MINIO_REGION,
)
 
def fetch_image(key):
    supported_formats = ['jpeg', 'jpg', 'png']
    try:
        extension = key.rsplit('.', 1)[1]
        if extension not in supported_formats:
            return

        start_time = time.time()
        print(f"Getting: {key}")
        obj = minio_client.get_object(Bucket=MINIO_BUCKET, Key=key)
        print(f"Got={key} Took={time.time()-start_time}s")
        image_bytes = obj["Body"].read()
        return key, image_bytes
    except Exception as e:
        print(f"Failed to fetch {key} : {e}")
        return key, None

def process_image(key, image_bytes):
    start_time = time.time()
    image = face_recognition.load_image_file(io.BytesIO(image_bytes))
    face_encodings = face_recognition.face_encodings(image)

    if not face_encodings:
        print(f"No face found in {key}")
        return

    face_encoding = face_encodings[0]
    name = os.path.splitext(os.path.basename(key))[0]
    print(f"Processed={key} took={time.time() - start_time}s")
    return face_encoding, name

def load_known_faces():
    try:
        response=minio_client.list_objects_v2(Bucket=MINIO_BUCKET)
        pprint(response)
        start_time = time.time()

        if 'Contents' not in response:
            print('No images found in bucket')
            return

        keys= [item["Key"] for item in response.get('Contents', [])][:5]

        with ThreadPoolExecutor(max_workers=20) as executor:
            fetch_results = list(executor.map(fetch_image, keys))

        for key, image_bytes in fetch_results:
            if image_bytes is None:
                continue

            result = process_image(key, image_bytes)
            if result:
                encoding, name = result
                known_face_encodings.append(encoding)
                known_face_names.append(name)
        print(f"Total time: {time.time() - start_time}")
    except Exception as e:
        print(e)


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
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        image = Image.open(io.BytesIO(file.read()))
        image = image.convert('RGB')  
        image_np = np.array(image)
        
        face_locations = face_recognition.face_locations(image_np)
        face_encodings = face_recognition.face_encodings(image_np, face_locations)
        
        tolerance = 0.5
        message = "No faces found in the image"  
       
        if not face_encodings:
            message = "No faces found in the image"

        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance=tolerance)

            if not any(matches):
                message = "No known face matched, attendance not recorded"
                continue
            
            face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
            name = "Unknown"

            first_match_index = matches.index(True)
            name = known_face_names[first_match_index]
            save_attendance(name)
            message = f"{name}"
            break  # Exit loop after first match (optional based on your needs)

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    return jsonify({'status': message}), 200

@app.route('/upload-image', methods=['POST'])
def upload_image():
    try:
        if 'file' not in request.files:
            raise ValueError('No file part')

        file = request.files['file']
        if file.filename == '':
            raise ValueError('No selected file')

        image = Image.open(file.stream)
        supported_formats = ['JPEG', 'JPG', 'PNG']
        
        if image.format not in supported_formats:
            new_image = io.BytesIO()
            image = image.convert('RGB')
            image.save(new_image, format='JPEG')
            new_image.seek(0)
            filename = f"{file.filename.rsplit('.', 1)[0]}.jpg"
            content_type = 'image/jpeg'
        else:
            file.stream.seek(0)
            new_image = file.stream
            filename = file.filename
            content_type = file.content_type

        minio_client.upload_fileobj(
            new_image,
            MINIO_BUCKET,
            filename,
            ExtraArgs={'ContentType': content_type}
        )   
        resp = jsonify({'message': 'Image uploaded successfully!'}), 200

    except Exception as e:
        resp = jsonify({'error': str(e)}), 500
        
    return resp

if __name__ == '__main__':
    load_known_faces()  
    app.run(debug=True)
