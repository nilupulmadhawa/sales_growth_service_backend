from fastapi import FastAPI
# Assuming the components directory contains recommendations and tracking modules.
# If your project structure is different, you may need to adjust these import paths.
from components.recommendations import router as recommendations_router
from components.tracking import router as tracking_router
from components.price_optimization import router as price_router
from components.products import router as products_router

app = FastAPI(title="Product Recommendation Service", version="1.0")

# Include routers from different components
app.include_router(recommendations_router, prefix="/api/v1/recommendations", tags=["Recommendations"])
app.include_router(tracking_router, prefix="/api/v1/tracking", tags=["Tracking"])
app.include_router(price_router, prefix="/api/v1/optimize", tags=["Optimize"])
app.include_router(products_router, prefix="/api/v1/products", tags=["Products"])


# Include the router that has the metrics endpoints
app.include_router(tracking_router)

# You can also define root-level endpoints directly in this file
@app.get("/")
async def root():
    return {"message": "Welcome to the Product Recommendation Service API!"}