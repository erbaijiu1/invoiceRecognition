FROM python:3.10.20

# ��װϵͳ������Poppler��PDFתͼƬ���裩����������
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ��װ���������� Docker ���棩
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ����Ӧ�ô���
COPY . .

EXPOSE 8999

# gunicorn ����ģʽ
CMD ["gunicorn", "--bind", "0.0.0.0:8999", "--workers", "1", "--timeout", "300", "app:app"]
