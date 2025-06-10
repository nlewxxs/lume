FROM python:3.12-slim

WORKDIR /app

COPY shared/ ./shared/ 
COPY flightcontroller/requirements.txt .
COPY flightcontroller/flightcontroller.py . 

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "-u", "flightcontroller.py"]
