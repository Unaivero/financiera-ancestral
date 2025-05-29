FROM python:3.10-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements_v2.txt
EXPOSE 5000
CMD ["python", "api_server.py"]
