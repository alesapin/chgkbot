# docker build -t alesapin/chgk-bot .
FROM ubuntu:18.04

RUN apt-get --allow-unauthenticated update -y \
    && env DEBIAN_FRONTEND=noninteractive \
    apt-get --allow-unauthenticated install --yes --no-install-recommends \
        bash \
        fakeroot \
        software-properties-common \
        gnupg \
        apt-transport-https \
        ca-certificates \
        python3 \
        python3-pip \
        build-essential \
        python3-dev \
        locales

RUN sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
    dpkg-reconfigure --frontend=noninteractive locales && \
    update-locale LANG=en_US.UTF-8

RUN pip3 install setuptools wheel
RUN pip3 install python-telegram-bot
RUN pip3 install python-Levenshtein
RUN pip3 install requests pymorphy2

COPY src /chgkbot
ENV LANG en_US.UTF-8
ENV PYTHONIOENCODING=utf-8
ENV TELEGRAM_TOKEN=''
ENV LOG_PATH='/log/stdout.txt'
ENV DB_PATH='/db/chgkdb'

CMD python3 /chgkbot/bot.py --token $TELEGRAM_TOKEN --log-path $LOG_PATH --db-path $DB_PATH
