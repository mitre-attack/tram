FROM python:3.7

RUN apt-get install -y git

WORKDIR /tram

COPY . .


RUN pip install -r /tram/requirements.txt

# Fix NLTK punkt issue by downloading it separately
RUN python /tram/nltk_download.py

EXPOSE 9999
CMD ["python", "tram.py"]
