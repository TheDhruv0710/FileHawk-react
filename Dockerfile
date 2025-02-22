FROM docker.repo1.uhc.com/python:3.12-alpine

# Set bash as default shell rather than sh
#!!!SHELL ["/bin/bash", "-c"]

# --------------------------------------------------------
# install misc helpers
# --------------------------------------------------------
RUN echo "--------------------------------------------------------------------"
RUN cat /etc/apk/repositories
RUN sed -i 's/dl-cdn.alpinelinux.org\/alpine/repo1.uhc.com\/artifactory\/dl-cdn/g' /etc/apk/repositories
RUN echo "--------------------------------------------------------------------"
RUN cat /etc/apk/repositories

RUN apk update && apk add --no-cache libaio libnsl libc6-compat curl unzip net-tools gcc musl-dev openssl libc-dev libffi-dev g++ make

# Set up pip to use UHG mirror rather than pythonhosted.org
RUN pip config set global.index-url https://repo1.uhc.com/artifactory/api/pypi/pypi-virtual/simple
RUN python -m ensurepip --upgrade
RUN pip install --upgrade pip
RUN pip install --upgrade setuptools

RUN mkdir -p /app/ && \
    chmod -R 777 /app

COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt


# Remove test folder
RUN rm -rf /usr/local/lib/python3.12/site-packages/future/backports/test

RUN python -m pip uninstall pip -y

COPY ./app/ /app/

RUN adduser -u 1001 pyrun --disabled-password

RUN chown -R 1001:0 /app/ && \
    chmod -R g+wrx /app/


USER 1001
EXPOSE 5000

CMD [ "sh", "/app/run.sh" ]
