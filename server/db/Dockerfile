FROM python:3.12-slim

WORKDIR /app

COPY shared/ ./shared/ 
COPY db/requirements.txt .
COPY db/training_db.py . 

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5432

CMD ["python", "training_db.py"]
