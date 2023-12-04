FROM python:3

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

CMD [ "python"]