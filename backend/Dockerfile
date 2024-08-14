FROM python:3.9

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt --no-cache-dir

COPY . . 
COPY entrypoint.sh .

CMD ["sh", "entrypoint.sh"]
