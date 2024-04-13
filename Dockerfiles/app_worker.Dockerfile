FROM python:3.10
ENV PYTHONUNBUFFERED 1

# Allows docker to cache installed dependencies between builds
COPY ./requirements.txt requirements.txt
RUN pip install -r requirements.txt
RUN rm -rf /code/static

# Adds our application code to the image
COPY . code
WORKDIR code

EXPOSE 8000

# Run the production server
# Runs backend + scheduler + worker at one go
CMD  bash prod.sh