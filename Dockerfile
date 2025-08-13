FROM python:3.11.11-bookworm

COPY requirements.txt .

RUN python -m pip install --upgrade pip -i https://mirrors.cloud.tencent.com/pypi/simple \ 
    && pip install -r requirements.txt -i https://mirrors.cloud.tencent.com/pypi/simple

WORKDIR /app
