FROM python:3.11-slim

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get update && apt-get upgrade -y
RUN playwright install
RUN playwright install-deps

EXPOSE 5000

CMD ["python", "app.py"]
