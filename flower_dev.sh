export FLOWER_UNAUTHENTICATED_API=1
celery -A sim_core flower --port=3000
