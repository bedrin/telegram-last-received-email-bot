FROM python:3-alpine

#RUN apk add py3-pip g++ make pkgconfig openssl-dev libffi-dev --upgrade
RUN apk add py3-pip g++ make pkgconfig openssl-dev libffi-dev --upgrade

WORKDIR /usr/src/app

ADD ./monitoring-bot.py /usr/src/app/monitoring-bot.py

RUN pip3 install pipenv
RUN pipenv install  --deploy --system --ignore-pipfile

CMD ["/usr/local/bin/python3", "/usr/src/app/monitoring-bot.py"]
