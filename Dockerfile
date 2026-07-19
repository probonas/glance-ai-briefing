FROM python:3-slim

COPY . /app
WORKDIR /app

RUN pip install --no-cache-dir .

ENV LLM_PROVIDER="deepseek"
ENV DEEPSEEK_API_KEY=""
ENV GOOGLE_AI_API_KEY=""
ENV GLANCE_CONFIG="/glance-config/config/home.yml"

EXPOSE 8080

CMD ["briefing", "serve", "--host", "0.0.0.0"]
