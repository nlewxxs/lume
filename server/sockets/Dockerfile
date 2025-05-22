FROM python:3.12-slim

WORKDIR /app

COPY shared/ ./shared/ 
COPY sockets/requirements.txt .
COPY sockets/sockets.py . 

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8888/udp

CMD ["python", "sockets.py"]
