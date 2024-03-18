import pandas as pd
from keras.models import load_model
from fastapi import APIRouter
from .models import OptimizeInput  # Adjust the import path as necessary
from datetime import date, datetime
import logging

router = APIRouter()

logger = logging.getLogger(__name__)

with open("price_optimization/price_optimization.h5", "rb") as f:
    model = load_model("price_optimization/price_optimization.h5") 

read_data = pd.read_csv('price_optimization/product_price_dataset.csv')

def get_price_optimization(product: str, product_category: str, cost: float, date: date) -> float:
    
    data = read_data
    maximum_profit_margin = 20
    minimum_profit_margin = 10
    data['Order_Date'] = pd.to_datetime(data['Order_Date'], errors='coerce')
    data['Product_Category'] = data['Product_Category'].fillna('No Category')

    data['maximum_profit_margin'] = maximum_profit_margin
    data['minimum_profit_margin'] = minimum_profit_margin

    data['day_of_week'] = data['Order_Date'].dt.day_name()
    data['month'] = data['Order_Date'].dt.month_name()

    # def week_of_month(dt):
    #     first_day = dt.replace(day=1)
    #     dom = dt.day
    #     adjusted_dom = dom + first_day.weekday()
    #     return int(np.ceil(adjusted_dom / 7))

    def week_of_month(dt):
        first_day = dt.replace(day=1)
        first_weekday = first_day.weekday()
        offset = (dt.day + first_weekday - 1) // 7
        return offset + 1

    data['week_of_month'] = data['Order_Date'].apply(week_of_month)

    data['cost'] = data['Sales'] - data['Profit']

    data['order_count'] = data.groupby(['Order_Date','Product'])['Quantity'].transform('sum')
    data['total_revenue_per_day'] =data['order_count'] * data['Sales']


    new_df = data.groupby(['Order_Date','Product_Category', 'Product','Sales', 'minimum_profit_margin','maximum_profit_margin','week_of_month','month','cost']).size().reset_index(name='order_count')

    # Sort the DataFrame by 'Order_Date'
    new_df.sort_values(by='Order_Date', inplace=True)

    new_df['average_sales_per_week_of_month'] = new_df.groupby(['month','week_of_month'])['order_count'].transform('mean')

    new_df['max'] = new_df.groupby(['week_of_month'])['average_sales_per_week_of_month'].transform('max')
    new_df['min'] = new_df.groupby(['week_of_month'])['average_sales_per_week_of_month'].transform('min')
    # Calculate 'demand' based on the grouped data

    new_df['demand'] =( new_df['average_sales_per_week_of_month'] - new_df['min'])/ ( new_df['max'] - new_df['min'])*100
    features = ['Product', 'Product_Category', 'cost', 'week_of_month','month']
    x= new_df[features]
    x = pd.get_dummies(x)
    sample_input = {
        'Product_'+product: 1,
        'Product_Category_'+product_category: 1,
        'cost': cost,
        'week_of_month': week_of_month(date),
        'month': 1
    }
    sample_df = pd.DataFrame([sample_input])

    sample_df = sample_df.reindex(columns=x.columns, fill_value=0)
    sample_df = pd.get_dummies(sample_df)
    
    prediction = model.predict(sample_df)

   
    return  cost + cost * (maximum_profit_margin +((maximum_profit_margin - minimum_profit_margin )* prediction[0][0] /100))/100

@router.post("/", response_model=float)  # More specific response 
def get_price_optimizations(optimize_input: OptimizeInput):
    prediction = get_price_optimization(
        product=optimize_input.product,
        product_category=optimize_input.product_category,
        cost=optimize_input.cost,
        date=optimize_input.date
    )
    return prediction 
