#!/bin/bash

# Function to start the backend server
start_backend() {
    echo "Migrating Database..."
    python3 manage.py migrate
    # python3 manage.py collectstatic

    echo "Starting Django backend..."
    gunicorn --timeout $TIMEOUT --bind 0.0.0.0:$PORT --workers=1 --access-logfile - sim_core.wsgi:application
}

# Function to start the Celery worker
start_worker() {
    echo "Starting Celery worker..."
    celery -A sim_core worker -B --loglevel=info
}

start_scheduler() {
    echo "Starting Scheduler..."
    celery -A sim_core beat --loglevel=debug --scheduler django_celery_beat.schedulers:DatabaseScheduler
}

start_redis() {
    echo "Starting Redis..."
    redis-server
}

# Function to stop processes gracefully
stop_processes() {
    echo "Stopping processes..."
    kill -SIGTERM $backend_pid $worker_pid $scheduler_pid
    redis-cli shutdown
    exit 0
}

# Start the backend server in the background
start_backend &
backend_pid=$!

# Start the Celery worker in the background
start_worker &
worker_pid=$!

# Start the scheduler in the background
start_scheduler &
scheduler_pid=$!

# Start Redis in the background
start_redis &
redis_pid=$!

# Set up trap to catch Ctrl+C and stop processes
trap stop_processes SIGINT SIGTERM

# Wait for all processes to finish
wait
