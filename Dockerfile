FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080
EXPOSE 8080

# Run as non-root
RUN adduser --disabled-password --gecos "" appuser
USER appuser

CMD ["python", "main.py"]
