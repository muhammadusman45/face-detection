# FROM python:3.12.5-slim

# WORKDIR /app

# COPY requirement.txt .

# RUN apt-get update && apt-get install -y \ 
#     cmake \
#     git \
#     build-essential \
#     libgl1 \
#     libglib2.0-0
# RUN pip install Flask 
# RUN pip install flask-restx
# RUN pip install --no-cache-dir Flask \
#     git+https://github.com/ageitgey/face_recognition_models \
#     face-recognition
# RUN 
# # RUN pip install --upgrade pip && \
# #     pip install --no-cache-dir -r requirement.txt

# COPY . .

# CMD ["flask", "run", "--host=0.0.0.0"]

# EXPOSE 5000

# Use an official Python 3.12.5 runtime as a parent image
FROM python:3.12.5-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirement file first
COPY requirement.txt .

# Install system dependencies including Git, CMake, and build tools
RUN apt-get update && apt-get install -y \
    cmake \
    git \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Flask and other necessary libraries
# RUN pip install Flask flask-restx

# Install face_recognition_models first from GitHub
# RUN pip install git+https://github.com/ageitgey/face_recognition_models

# Install face-recognition after models
# RUN pip install face-recognition
RUN pip install -r requirement.txt
# Optionally, install from requirement.txt if there are additional dependencies
# RUN pip install --no-cache-dir -r requirement.txt

# Copy the current directory contents into the container
COPY . .
ENV FLASK_APP=app:app   
COPY uploaded_images /uploaded_images
RUN chmod -R 755 /uploaded_images
# Run the Flask app when the container launches
CMD ["flask", "run", "--host=0.0.0.0"]

# Make port 5000 available to the world outside this container
EXPOSE 5000

