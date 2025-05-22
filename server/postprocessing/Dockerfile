FROM python:3.12-slim

WORKDIR /app

COPY shared/ ./shared/ 
COPY postprocessing/requirements.txt .
COPY postprocessing/post_processing.py . 

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "post_processing.py"]
