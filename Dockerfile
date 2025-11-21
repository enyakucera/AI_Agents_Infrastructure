
FROM python:3.10

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY real_estate_agent.py .

CMD ["python", "real_estate_agent.py"]
