#!/bin/bash

# Function to start the backend server
start_backend() {
    echo "Migration Database..."
    python3 manage.py migrate

    echo "Starting Django backend..."
    # Replace 'python manage.py runserver' with your actual command to start the Django server
    python3 manage.py runserver
}


# Function to start the Celery worker
start_worker() {
    echo "Starting Celery worker..."
    celery -A sim_core worker -B --loglevel=info
}

start_scheduler() {
    echo "Starting start_scheduler"
    celery -A sim_core beat --loglevel=debug --scheduler django_celery_beat.schedulers:DatabaseScheduler
}

# Function to stop both backend and worker processes
stop_processes() {
    echo "Stopping processes..."
    # Kill the background processes
    kill "$backend_pid"
    kill "$worker_pid"
    kill "$scheduler_pid"
    exit 0
}

# Start the backend server in the background
start_backend &
backend_pid=$!

# Start the Celery worker in the background
start_worker &
worker_pid=$!

start_scheduler &
scheduler_pid=$!

# Set up trap to catch Ctrl+C and stop both processes
trap stop_processes SIGINT

# Wait for both processes to finish
wait
