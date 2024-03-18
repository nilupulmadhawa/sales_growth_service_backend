from pydantic import BaseModel
from datetime import datetime
from typing import Optional


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

class CombinedData(BaseModel):
    product_name: str
    category_code: str
    brand: str
    age: int
    gender: str
    location: str
    event_type: str
    event_time: datetime
    
    class Config:
        orm_mode = True

class UserDemographic(BaseModel):
    user_id: Optional[int] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    location: Optional[str] = None

class UserUpdate(BaseModel):
    user_id: int
    age: int
    gender: str
    location: str