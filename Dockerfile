# Nurture — container image for Hugging Face Spaces / Render / any Docker host
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=7860 HOST=0.0.0.0
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# Retrain inside the image so the saved models always match this scikit-learn version.
RUN python train_models.py > /dev/null && mkdir -p app_data && chmod -R 777 app_data

EXPOSE 7860
CMD ["python", "server.py"]
