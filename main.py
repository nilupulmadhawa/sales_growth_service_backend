from fastapi import FastAPI
# Assuming the components directory contains recommendations and tracking modules.
# If your project structure is different, you may need to adjust these import paths.
from components.recommendations import router as recommendations_router
from components.tracking import router as tracking_router
from components.combined_data import router as combined_data_router
from components.user_demo_data import router as user_demo_data_router

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Product Recommendation Service", version="1.0")

origins = [
    # any
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allows specified origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


# Include routers from different components
app.include_router(recommendations_router, prefix="/recommendations", tags=["Recommendations"])
app.include_router(tracking_router, tags=["Tracking"])
app.include_router(combined_data_router)
app.include_router(user_demo_data_router)

# You can also define root-level endpoints directly in this file
@app.get("/")
async def root():
    return {"message": "Welcome to the Product Recommendation Service API!"}