# Use an official Python runtime as a parent image
FROM python:3.9-slim-buster

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file to the container
COPY requirements.txt .

# Install any dependencies
RUN pip install -r requirements.txt --no-cache-dir

# Copy the application code to the container
COPY . .

# Expose the port that your application listens on (default: 5000, check your app)
EXPOSE 5000

# Define the command to run your application
CMD ["python", "app.py"]

