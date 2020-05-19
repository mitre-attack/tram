FROM python:3.8.2-buster

# Install necessary python dependencies
COPY requirements.txt tram/

RUN pip3 install --upgrade cython
RUN pip3 install -r tram/requirements.txt
RUN python3 -m nltk.downloader punkt

# Copy all the files to the container
COPY conf/. tram/conf/
COPY database/*.py tram/database/
COPY handlers/. tram/handlers/
COPY models/. tram/models/
COPY service/. tram/service/
COPY webapp/. tram/webapp/
COPY tram.py tram/tram.py

WORKDIR /tram

EXPOSE 9999

CMD ["python3", "tram.py"]
