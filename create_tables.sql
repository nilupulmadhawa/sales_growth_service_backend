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
    event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Create Impressions Table
CREATE TABLE IF NOT EXISTS impressions (
    impression_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(255),
    product_id INT,
    impression_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Create Clicks Table
CREATE TABLE IF NOT EXISTS clicks (
    click_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(255),
    product_id INT,
    click_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS conversion_rates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    month VARCHAR(7),
    total_trials INT,
    total_conversions INT,
    conversion_rate DECIMAL(10, 2)
);

