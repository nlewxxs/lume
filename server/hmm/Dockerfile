FROM python:3.12-slim

WORKDIR /app

COPY shared/ ./shared/ 
COPY hmm/requirements.txt .
COPY hmm/hmm.py . 

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5432

CMD ["python", "hmm.py"]
