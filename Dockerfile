# Use an official lightweight Python image as a parent image
# Using a specific version is better than using 'latest'
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the file that lists the dependencies
COPY requirements.txt .

# Install the dependencies from the requirements file
# --no-cache-dir makes the image smaller
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application's code into the container
COPY . .

# Specify the command to run when the container starts.
# While the Dokploy scheduler will run 'python main.py' directly,
# this is good practice for defining the container's default behavior.
CMD ["python", "main.py"]
