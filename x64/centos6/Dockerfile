FROM centos:6

WORKDIR /opt/python


RUN yum -y update && \
    yum -y install \
    glibc-devel \
    gcc \
    gcc-c++ \
    make \
    openssl-devel \
    sqlite-devel \
    libffi-devel \
    zlib-devel \
    wget \
    xz \
    tar \
    unzip

RUN wget -qO- https://www.python.org/ftp/python/3.5.2/Python-3.5.2.tar.xz | tar xJ

WORKDIR /opt/python/Python-3.5.2
RUN ./configure --prefix=/opt/python/python
RUN make -j4
RUN make install
