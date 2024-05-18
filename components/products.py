from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List, Optional, Dict, Any
import aiomysql
from pydantic import BaseModel, Field 
from .database import DB_CONFIG, get_db_connection
from fastapi import HTTPException
import httpx  # httpx is used for making asynchronous HTTP requests
import requests
import json
import numpy as np
from decimal import Decimal
from datetime import datetime, timedelta

router = APIRouter()


class ProductBase(BaseModel):
    product_id: str = Field(..., min_length=1) 
    product_name: str = Field(..., min_length=1) 
    product_category: str = Field(..., min_length=1)
    product_brand: str = Field(..., min_length=1)
    department: str = Field(..., min_length=1)
    cost: float = Field(..., gt=0)
    selling_price: float = Field(..., gt=0)
    max_margin: float
    min_margin: float

class ProductCreate(ProductBase):
    pass  # All fields are required

class ProductUpdate(ProductBase):
    product_id: str | None = None
    product_name: str | None = None
    product_category: str | None = None
    product_brand: str | None = None
    cost: float | None = None
    selling_price: float | None = None
    max_margin: float | None = None
    min_margin: float | None = None

class Product(ProductBase):
    id: int

    class Config:
        orm_mode = True  # For potential SQLAlchemy compatibility

class ProductResponse(BaseModel):
    product_id: str
    product_name: str 
    product_category: str 
    product_brand: str 
    cost: float 
    selling_price: float 
    max_margin: Optional[float] = None
    min_margin: Optional[float] = None
    department: Optional[str] = None 

class ProductListResponse(BaseModel):
    title: str
    data: List[ProductResponse]


async def get_product_by_id(product_id: int) -> Optional[Product]:
    async with await get_db_connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT * FROM products WHERE id = %s", (product_id))
            product_dict = await cursor.fetchone()
            await cursor.close()
            return product_dict if product_dict else None

async def create_product(product: ProductCreate) -> Product:
    async with await get_db_connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "INSERT INTO products (product_id, product_name, product_category, product_brand, selling_price, cost, max_margin, min_margin,department) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (product.product_id, product.product_name, product.product_category, product.product_brand, product.selling_price, product.cost, product.max_margin, product.min_margin)
            )
            last_row_id = cursor.lastrowid
            await conn.commit()
            await cursor.close()
            return await get_product_by_id(last_row_id)


async def get_all_products() -> ProductListResponse:
    product_query = "SELECT product_id, product_name, product_category, product_brand, selling_price, cost, max_margin, min_margin, department FROM products LIMIT 1000"
    async with get_db_connection() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cusr:
            await cusr.execute(product_query)
            products = await cusr.fetchall()
            product_list = [ProductResponse(**product) for product in products]
            return product_list


async def update_product(product_id: int, product: ProductUpdate) -> Product:
    async with await get_db_connection() as conn:
        current_product = await get_product_by_id(product_id)
        if not current_product:
            raise HTTPException(status_code=404, detail="Product not found")

        update_data = product.dict(exclude_unset=True)  # Only update provided fields 
        update_query = ", ".join([f"{field} = %s" for field in update_data])
        async with conn.cursor() as cursor:
            await cursor.execute(
            f"UPDATE products SET {update_query} WHERE id = %s",
            (*update_data.values(), product_id)
            )
            await conn.commit()
            return await get_product_by_id(product_id)

async def delete_product(product_id: int) -> None:
    async with await get_db_connection() as conn:
        current_product = await get_product_by_id(product_id)
        if not current_product:
            raise HTTPException(status_code=404, detail="Product not found")

        await conn.cursor().execute("DELETE FROM products WHERE id = %s", (product_id))
        await conn.commit()

# --- API Endpoints --- 
@router.get("/", response_model=List)
async def list_products():
    product = await get_all_products()
    if not product: 
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.get("/{product_id}")
async def get_product(product_id: int):
    product = await get_product_by_id( product_id)
    if not product: 
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.post("/", status_code=201)
async def add_product(product: ProductBase ):
    return await create_product( product)

@router.put("/{product_id}")
async def update_products(product_id: int, product: ProductUpdate):
    return await update_product(product_id, product)

@router.delete("/{product_id}")
async def remove_product(product_id: int):
    await delete_product(product_id)
    return {"message": "Product deleted successfully"}
