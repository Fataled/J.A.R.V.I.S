FROM python:3.12.5

LABEL authors="brumeako"

WORKDIR /J.A.R.V.I.S

ENV PYTHONUNBUFFERED=1

COPY server/requirements.txt .

RUN apt-get update && apt-get install -y portaudio19-dev libsndfile1 ffmpeg && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt

COPY server/ .

EXPOSE 8000

CMD ["uvicorn", "websocket:app", "--host", "0.0.0.0", "--port", "8000"]
