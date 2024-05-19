from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from components.recommend_products import router as recommendations_router
from components.cold_start_solution import router as cold_start_recommendations_router
from components.tracking import router as tracking_router
from components.price_optimization import router as price_router
from components.products import router as products_router
from components.sales_forecasting import router as sales_forecasting_router
from components.promotion import router as promotion_router
from components.combined_data import router as combined_data_router
from components.user_demo_data import router as user_demo_data_router

app = FastAPI(title="Product Recommendation Service", version="1.0")

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allows specified origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Security and authentication setup
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

fake_users_db = {
    "admin": {
        "username": "admin",
        "full_name": "Admin User",
        "email": "admin@gmail.com",
        "hashed_password": "admin123", 
        "disabled": False,
    }
}

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None

class User(BaseModel):
    username: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = None

class UserInDB(User):
    hashed_password: str

def verify_password(plain_password, hashed_password):
    return plain_password == hashed_password

def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)

def authenticate_user(fake_db, username: str, password: str):
    user = get_user(fake_db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"access_token": user.username, "token_type": "bearer"}

@app.get("/users/me", response_model=User)
async def read_users_me(token: str = Depends(oauth2_scheme)):
    user = get_user(fake_users_db, token)
    if user is None:
        raise HTTPException(status_code=400, detail="Invalid authentication credentials")
    return user

# Include routers from different components
app.include_router(recommendations_router, prefix="/api/v1/recommendations", tags=["Recommendations"])
app.include_router(cold_start_recommendations_router, prefix="/api/v1/cold-start-recommendations", tags=["ColdStartRecommendations"])
app.include_router(tracking_router, prefix="/api/v1/tracking", tags=["Tracking"])
app.include_router(price_router, prefix="/api/v1/optimize", tags=["Optimize"])
app.include_router(products_router, prefix="/api/v1/products", tags=["Products"])
app.include_router(sales_forecasting_router, prefix="/api/v1/sales-forecasting", tags=["Sales Forecasting"])
app.include_router(promotion_router, prefix="/api/v1/promotion", tags=["Promotion"])
app.include_router(user_demo_data_router, prefix="/api/v1/user-demo-data", tags=["User Demo Data"])
app.include_router(combined_data_router, prefix="/api/v1", tags=["Combined Data"])
app.include_router(tracking_router, prefix="/api/v1", tags=["Tracking"])

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Welcome to the Product Recommendation Service API!"}
