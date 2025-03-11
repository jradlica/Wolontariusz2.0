# Use an official Python runtime as a parent image
FROM python:3.9

# Set the working directory in the container
WORKDIR /app

# Install any dependencies
RUN pip install --no-cache-dir fastapi uvicorn pytz bcrypt
# Copy the backend.py file
COPY backend.py /app/

# Copy the static files
COPY static /app/static

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define environment variable
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["uvicorn", "backend:app", "--host", "0.0.0.0", "--port", "8000", "--ssl-keyfile", "/app/key.pem", "--ssl-certfile", "/app/cert.pem"]
