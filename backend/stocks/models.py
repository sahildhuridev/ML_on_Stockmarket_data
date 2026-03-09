from django.db import models

# Create your models here.
from django.db import models
from portfolios.models import Portfolio

class Stock(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="stocks")
    ticker = models.CharField(max_length=20)
    company_name = models.CharField(max_length=255)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.ticker