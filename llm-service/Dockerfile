FROM pytorch/pytorch:2.4.1-cuda12.1-cudnn9-runtime

ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
ENV TOKENIZERS_PARALLELISM=false

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY app ./app

ENV MODEL_DIR=/models/qwen35_9b_hrmatch_merged

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]