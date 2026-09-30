FROM nikolaik/python-nodejs:python3.11-nodejs20

# Set working directory
WORKDIR /app

# Copy the entire project
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Node dependencies and build the webapp
WORKDIR /app/webapp
RUN npm install
RUN npm run build

# Go back to root
WORKDIR /app

# Make the start script executable
RUN chmod +x start.sh

# Start the application
CMD ["./start.sh"]
