FROM ubuntu:16.04

WORKDIR /opt/python


RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    make \
    automake \
    gcc \
    g++ \
    libc6-dev \
    pkg-config \
    libffi-dev \
    libssl-dev \
    libsqlite3-dev \
    zlib1g-dev \
    wget \
    unzip \
    xz-utils \
    ca-certificates
RUN wget -qO- https://www.python.org/ftp/python/3.5.2/Python-3.5.2.tar.xz | tar xJ

WORKDIR /opt/python/Python-3.5.2
RUN ./configure --prefix=/opt/python/python
RUN make -j4
RUN make install
