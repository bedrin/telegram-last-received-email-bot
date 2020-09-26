FROM python:3-alpine

#RUN apk add py3-pip g++ make pkgconfig openssl-dev libffi-dev --upgrade
RUN apk add py3-pip g++ make pkgconfig openssl-dev libffi-dev --upgrade

COPY . /usr/src/app
WORKDIR /usr/src/app

RUN pip3 install pipenv
RUN pipenv install  --deploy --system --ignore-pipfile

CMD ["/usr/local/bin/python3", "/usr/src/app/monitoring-bot.py"]
