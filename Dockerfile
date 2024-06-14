FROM python:3.11-alpine

WORKDIR /var/phoenixd_lnurl

RUN \
    apk update && \
    apk add \
        # secp256k1 requirements
        automake \
        build-base \
        libffi-dev \
        libtool \
        pkgconfig \
    ;

COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app ./app
COPY ./phoenixd-lnurl.env .

CMD ["uvicorn", "app.main:app_factory", "--workers", "1", "--factory", "--proxy-headers", "--host", "0.0.0.0", "--port", "8000"]
