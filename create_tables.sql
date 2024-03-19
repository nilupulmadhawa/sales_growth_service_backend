-- Create Users Table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(255),
    age INT,
    gender VARCHAR(10),
    location VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create Products Table
CREATE TABLE IF NOT EXISTS products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_name VARCHAR(255),
    product_category VARCHAR(255),
    product_Brand VARCHAR(255),
    cost DECIMAL(10, 2),
    selling_price DECIMAL(10, 2),
    max_margin DECIMAL(10, 2),
    min_margin DECIMAL(10, 2)
);

-- Create Events Table
CREATE TABLE IF NOT EXISTS events (
    event_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(255),
    product_id INT,
    event_type ENUM('view', 'cart', 'purchase'),
    event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create Impressions Table
CREATE TABLE IF NOT EXISTS impressions (
    impression_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(255),
    product_id INT,
    impression_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create Clicks Table
CREATE TABLE IF NOT EXISTS clicks (
    click_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(255),
    product_id INT,
    click_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS conversion_rates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    month VARCHAR(7),
    total_trials INT,
    total_conversions INT,
    conversion_rate DECIMAL(10, 2)
);

-- brand table
CREATE TABLE IF NOT EXISTS brands (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(255),
    brand VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- user preferences table
CREATE TABLE IF NOT EXISTS user_preferences (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(255),
    product_id INT,
    category VARCHAR(255),
    product_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- sales table make all nullable
CREATE TABLE IF NOT EXISTS sales (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(255) NULL,
    product_id VARCHAR(255),
    product_name VARCHAR(255) NULL,
    product_category VARCHAR(255) NULL,
    cost DECIMAL(10, 2) NULL,
    selling_price DECIMAL(10, 2),
    margin DECIMAL(10, 2) NULL,
    quantity INT,
    amount DECIMAL(10, 2),
    order_id VARCHAR(255),
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);