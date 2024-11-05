FROM python:3.10
ENV PYTHONUNBUFFERED 1

# Install Redis
RUN apt-get update && apt-get install -y redis-server libmpfr-dev libmpc-dev && rm -rf /var/lib/apt/lists/*

# Allows docker to cache installed dependencies between builds
COPY ./requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

# Adds our application code to the image
COPY . /code
WORKDIR /code

EXPOSE 8000
EXPOSE 6379

# Run the production server and Redis
CMD ["bash", "prod.sh"]
