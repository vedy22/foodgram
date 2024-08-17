FROM python:3.9-slim
WORKDIR /app
COPY . .
COPY entrypoint.sh .
RUN pip install -r requirements.txt --no-cache-dir
RUN apt-get update
RUN apt-get -y install fonts-dejavu
CMD ["sh", "entrypoint.sh"]