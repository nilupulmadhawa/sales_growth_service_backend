# sales_growth_service_backend

# command for table creation
# first install the package

pip install databases[aiomysql]


```

 Get-Content create_tables.sql | mysql -u root -p quixellai_db

 ```

 # start command


```
uvicorn main:app --reload

```