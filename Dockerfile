FROM python:3.12-alpine

WORKDIR /var/phoenixd_lnurl

COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app ./app
COPY ./phoenixd-lnurl.env .

CMD ["uvicorn", "app.main:app_factory", "--workers", "1", "--factory", "--proxy-headers", "--host", "0.0.0.0", "--port", "8000"]
