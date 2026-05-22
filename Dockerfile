FROM python:3.10-slim

# 安装系统依赖：Poppler（PDF转图片）、libGL（OpenCV）、字体
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先装依赖（利用 Docker 缓存）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 预下载 PaddleOCR 模型（加速首次启动）
RUN python -c "from paddleocr import PaddleOCR; PaddleOCR(use_angle_cls=True, lang='ch', show_log=False)"

# 复制应用代码
COPY . .

EXPOSE 8999

# gunicorn 生产模式：--preload 预加载 OCR 模型共享内存，2 worker，超时 300s
CMD ["gunicorn", "--bind", "0.0.0.0:8999", "--workers", "2", "--timeout", "300", "--preload", "app:app"]
