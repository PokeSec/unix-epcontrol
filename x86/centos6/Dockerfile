FROM pokesec/base-x86-centos6

WORKDIR /opt/python

RUN (linux32 yum -y update && \
    linux32 yum -y install \
    glibc-devel \
    gcc \
    gcc-c++ \
    make \
    openssl-devel \
    sqlite-devel \
    libffi-devel \
    zlib-devel \
    xz \
    wget \
    tar \
    unzip) || true

RUN linux32 yum -y update && \
    linux32 yum -y install \
    glibc-devel \
    gcc \
    gcc-c++ \
    make \
    openssl-devel \
    sqlite-devel \
    libffi-devel \
    zlib-devel \
    xz \
    wget \
    tar \
    unzip

RUN wget -qO- https://www.python.org/ftp/python/3.5.2/Python-3.5.2.tar.xz | tar xJ

WORKDIR /opt/python/Python-3.5.2
RUN linux32 ./configure --prefix=/opt/python/python
RUN linux32 make -j4
RUN linux32 make install
