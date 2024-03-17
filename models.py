from pydantic import BaseModel

class UserInput(BaseModel):
    age: float
    gender: str
    location: str
    num_recommendations: int = 5

class Metrics(BaseModel):
    impressions: int
    clicks: int

class Event(BaseModel):
    user_id: int
    product_id: int
    event_type: str