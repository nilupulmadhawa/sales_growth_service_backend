from pydantic import BaseModel
from datetime import date, datetime

class Metrics(BaseModel):
    impressions: int
    clicks: int

class OptimizeInput(BaseModel):
    product: str
    product_category: str
    cost: float
    date: date
    maxProfitMargin:float
    minProfitMargin:float

