FROM python:3.6-slim-jessie
MAINTAINER wangkun_lc@inspur.com

RUN mkdir /viscom /viscom/instance

COPY setup.py /viscom/setup.py
COPY viscom /viscom/viscom

WORKDIR /viscom
RUN pip install -i http://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com -e .

WORKDIR /
VOLUME [ "/viscom/instance" ]
EXPOSE 5000

ENV FLASK_APP viscom
ENV FLASK_ENV development

CMD [ "flask", "run", "-h", "0.0.0.0"]