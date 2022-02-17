FROM python:3

COPY requirements.txt app/
COPY proxy.py app/

WORKDIR /app
RUN pip install -r requirements.txt

CMD ["gunicorn", "-w", "1", "proxy:application"]
