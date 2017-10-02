FROM python:2.7
ADD . .
WORKDIR .
RUN pip install -r requirements.txt
