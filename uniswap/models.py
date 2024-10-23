from django.db import models

from core.models import BaseModel, Transaction

class PairCreated(Transaction):
    token0 = models.CharField(max_length=255)
    token1 = models.CharField(max_length=255)
    pair = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.token0=} {self.token1=} {self.pair=}"