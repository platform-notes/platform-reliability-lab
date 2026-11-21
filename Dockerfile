FROM python:3.15-alpine@sha256:0f9552bb28711333da16915ec146f5e6bb44a7fdac9ced15dc17c2e0206346dd

RUN apk add --no-cache 'krb5-libs=1.22.3-r0' \
    && python -m pip uninstall --yes --no-input pip \
    && rm -rf /root/.cache /usr/local/lib/python3*/ensurepip/_bundled \
    && ! python -m pip --version 2>/dev/null

WORKDIR /app

COPY src /app/src

USER 10001:10001

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

EXPOSE 8080

CMD ["python", "-m", "src.service"]
