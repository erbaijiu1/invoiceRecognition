FROM python:3.10-slim

# 锟斤拷装系统锟斤拷锟斤拷锟斤拷Poppler锟斤拷PDF转图片锟斤拷锟借）锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 锟斤拷装锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷 Docker 锟斤拷锟芥）
COPY requirements.txt .
RUN pip install --no-cache-dir -i https://mirrors.cloud.tencent.com/pypi/simple -r requirements.txt

# 锟斤拷锟斤拷应锟矫达拷锟斤拷
COPY . .

EXPOSE 8999

# gunicorn 锟斤拷锟斤拷模式
CMD ["gunicorn", "--bind", "0.0.0.0:8999", "--workers", "1", "--timeout", "300", "app:app"]
