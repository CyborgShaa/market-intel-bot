# Use a modern, specific, and lightweight Python version (from our file)
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy ALL our project files into the container (from our file)
COPY . .

# Keep the container running in a dormant state, ready for the scheduler (from your file)
CMD ["sleep", "infinity"]
