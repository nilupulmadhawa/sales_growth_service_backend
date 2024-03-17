-- Create Users Table
CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    age INT,
    gender VARCHAR(10),
    location VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create Products Table
CREATE TABLE IF NOT EXISTS products (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    product_name VARCHAR(255),
    category_code VARCHAR(255),
    brand VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create Events Table
CREATE TABLE IF NOT EXISTS events (
    event_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    product_id INT,
    event_type ENUM('view', 'cart', 'purchase', 'impression', 'click'),
    event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    state BOOLEAN DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

-- Create Impressions Table
CREATE TABLE IF NOT EXISTS impressions (
    impression_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    product_id INT,
    impression_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

-- Create Clicks Table
CREATE TABLE IF NOT EXISTS clicks (
    click_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    product_id INT,
    click_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);
