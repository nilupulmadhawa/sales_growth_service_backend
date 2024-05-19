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
    department: str
    optimized_price: float | None = None

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
    department: str | None = None
    optimized_price: float | None = None

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
    optimized_price: Optional[float] = None

class ProductListResponse(BaseModel):
    title: str
    count: int 
    data: List[ProductResponse]


async def get_product_by_id(product_id: int) -> Optional[Product]:
    async with get_db_connection() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cusr:
            await cusr.execute("SELECT * FROM products WHERE product_id = %s", (product_id))
            product_dict = await cusr.fetchone()
            await cusr.close()
            return product_dict if product_dict else None

async def create_product(product: ProductCreate) -> Product:
    async with await get_db_connection() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cusr:
            await cusr.execute(
                "INSERT INTO products (product_id, product_name, product_category, product_brand, selling_price, cost, max_margin, min_margin,department) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (product.product_id, product.product_name, product.product_category, product.product_brand, product.selling_price, product.cost, product.max_margin, product.min_margin)
            )
            last_row_id = cusr.lastrowid
            await conn.commit()
            await cusr.close()
            return await get_product_by_id(last_row_id)


async def get_all_products(page: int = 1, limit: int = 10) -> ProductListResponse:
    offset = (page - 1) * limit
    product_query = """
    SELECT product_id, product_name, product_category, product_brand, selling_price, cost, max_margin, min_margin, department
    FROM products
    LIMIT %s OFFSET %s
    """
    count_query = "SELECT COUNT(*) as total FROM products"

    async with get_db_connection() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cusr:
            # Execute the count query
            await cusr.execute(count_query)
            total_count = (await cusr.fetchone())['total']

            # Execute the product query
            await cusr.execute(product_query, (limit, offset))
            products = await cusr.fetchall()
            product_list = [ProductResponse(**product) for product in products]

            return ProductListResponse(
                title="List of products",
                count=total_count,
                data=product_list
            )



async def update_product(product_id: int, product: ProductUpdate) -> Product:
    async with get_db_connection() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cusr:
            current_product = await get_product_by_id(product_id)
            if not current_product:
                raise HTTPException(status_code=404, detail="Product not found")

            update_data = product.dict(exclude_unset=True)  # Only update provided fields 
            update_query = ", ".join([f"{field} = %s" for field in update_data])
            async with conn.cursor(aiomysql.DictCursor) as cusr:
                aa = await cusr.execute(
                f"UPDATE products SET {update_query} WHERE product_id = %s",
                (*update_data.values(), product_id)
                )
                await conn.commit()
                update_price_ecommerce(product_id, product)
                return await get_product_by_id(product_id)  

async def update_price_ecommerce(product_id: int, product: ProductUpdate) -> Product:
    async with get_db_connection() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cusr:
            await cusr.execute("SELECT price_update_url FROM op_configuration WHERE id = 1")
            url = await cusr.fetchone()
            print(url)
            

async def delete_product(product_id: int) -> None:
    async with await get_db_connection() as conn:
        current_product = await get_product_by_id(product_id)
        if not current_product:
            raise HTTPException(status_code=404, detail="Product not found")

        await conn.cursor(aiomysql.DictCursor).execute("DELETE FROM products WHERE product_id = %s", (product_id))
        await conn.commit()


# --- API Endpoints --- 
@router.get("/", response_model=ProductListResponse)
async def list_products(page: int = 1, limit: int = 10):
    product = await get_all_products(page, limit)
    if not product: 
        raise HTTPException(status_code=404, detail="Products not found")
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




class OpConfigUpdate(BaseModel):
    send_report: Optional[int] = None
    verifying_required: Optional[int] = None
    price_update_url: Optional[str] = None

class OpConfigResponse(BaseModel):
    id: int
    send_report: Optional[int] = None
    verifying_required: Optional[int] = None
    price_update_url: Optional[str] = None
    # auto_update_date: Optional[str] = None

async def get_op_configuration_by_id(config_id: int) -> Optional[Dict[str, Any]]:
    async with get_db_connection() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cusr:
            await cusr.execute("SELECT * FROM op_configuration WHERE id = %s", (config_id,))
            config_dict = await cusr.fetchone()
            return config_dict if config_dict else None

async def update_op_configuration(config_id: int, config: OpConfigUpdate) -> Dict[str, Any]:
    async with get_db_connection() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cusr:
            current_config = await get_op_configuration_by_id(config_id)
            if not current_config:
                raise HTTPException(status_code=404, detail="Configuration not found")

            update_data = config.dict(exclude_unset=True)
            update_query = ", ".join([f"{field} = %s" for field in update_data])
            await cusr.execute(
                f"UPDATE op_configuration SET {update_query} WHERE id = %s",
                (*update_data.values(), config_id)
            )
            await conn.commit()
            return await get_op_configuration_by_id(config_id)
        
async def get_op_configuration_by_id(config_id: int) -> Optional[OpConfigResponse]:
    async with get_db_connection() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cusr:
            await cusr.execute("SELECT * FROM op_configuration WHERE id = %s", (config_id,))
            config_dict = await cusr.fetchone()
            if config_dict:
                return OpConfigResponse(**config_dict)
            return None
        
@router.get("/op_configuration/{config_id}", response_model=OpConfigResponse)
async def get_op_configuration_endpoint(config_id: int):
    config = await get_op_configuration_by_id(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return config

@router.put("/op_configuration/{config_id}", response_model=Dict[str, Any])
async def update_op_configuration_endpoint(config_id: int, config: OpConfigUpdate):
    updated_config = await update_op_configuration(config_id, config)
    if not updated_config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return {"message": "Configuration updated successfully", "data": updated_config}
