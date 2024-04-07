import json
import os
from django.conf import settings

def parquet_files_to_process(ingested, label):
    result = []
    if isinstance(ingested, str):
        ingested = json.loads(ingested)
    
    os.chdir(os.path.join(settings.MEDIA_ROOT, f"logs__{label}"))
    if not isinstance(ingested, list):
        raise Exception("ingested should be a list")
    try:
        result.append(sorted(ingested)[-1])
    except IndexError:
        pass

    for i in os.listdir():
        if i not in ingested:
            result.append(i)
    after_ingestion = list(set(result + ingested))
    return result, after_ingestion
