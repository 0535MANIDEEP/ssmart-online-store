# Use the latest slim Python image (Python 3.13 is the current default)
FROM python:3.13-slim

# Set a working directory inside the container
WORKDIR /app

# Copy the application source code (the entire “app” package)
COPY app/ ./app/

# Copy the .env file – it contains the secret key & bcrypt hashes
COPY .env ./.env

# Install Python dependencies
# (fastapi + uvicorn are required; add any others you actually use)
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port FastAPI will run on
EXPOSE 8000

# Start the server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
