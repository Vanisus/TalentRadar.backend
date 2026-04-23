FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 python3-pip git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Скопировать модель в образ, если она лежит рядом
# COPY qwen35_9b_hrmatch_merged /app/qwen35_9b_hrmatch_merged
# или смонтировать томом при запуске

COPY app ./app

ENV MODEL_DIR=/app/qwen35_9b_hrmatch_merged

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]