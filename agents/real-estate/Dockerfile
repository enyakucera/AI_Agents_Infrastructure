FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY agent.py .
COPY sources.json .
COPY agent_config.json .

CMD ["python", "-u", "agent.py"]
