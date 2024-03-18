from pydantic import BaseModel

class UserInput(BaseModel):
    age: float
    gender: str
    location: str
    num_recommendations: int = 5

class Metrics(BaseModel):
    impressions: int
    clicks: int

class OptimizeInput(BaseModel):
    product: str
    product_category: str
    cost: float
    date: any
