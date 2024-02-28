FROM python:3.11-slim

WORKDIR /code

COPY ./requirements_cloud.txt /code/requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./static /code/static
COPY ./routers_cloud /code/routers_cloud
COPY ./backend_cloud.py /code/

EXPOSE 80

CMD ["uvicorn", "backend_cloud:app", "--host", "0.0.0.0", "--port", "80"]
