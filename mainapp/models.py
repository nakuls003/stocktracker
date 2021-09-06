from django.db import models
from django.contrib.auth.models import User


class StockDetail(models.Model):
    stock_name = models.CharField(max_length=255, unique=True)
    user = models.ManyToManyField(User)

    def __str__(self):
        return "<{}>".format(self.stock_name)
