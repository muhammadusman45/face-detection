FROM python:3.12.5-slim

WORKDIR /app

COPY requirement.txt .

RUN apt-get update && apt-get install -y \
    cmake \
    git \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install -r requirement.txt

COPY . .
ENV FLASK_APP=app:app   
COPY uploaded_images /uploaded_images
RUN chmod -R 755 /uploaded_images

CMD ["flask", "run", "--host=0.0.0.0"]
EXPOSE 5000

