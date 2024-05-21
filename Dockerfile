FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt /app

RUN pip install --no-cache-dir -r requirements.txt

# Create directory for AWS credentials
RUN mkdir -p /root/.aws

COPY . /app

EXPOSE 8501
CMD ["streamlit", "run", "--server.port", "8501", "app.py"]
