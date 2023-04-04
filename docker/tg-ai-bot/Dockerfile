# Use a lightweight Python image as the base image
FROM python:3.11-slim-buster

# Set the working directory to /app
WORKDIR /app

# Copy the requirements file into the container
COPY pyproject.toml ./
COPY google_service_credentials.json ./

# Install the dependencies using Poetry
RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev

# Copy the rest of the application code into the container
COPY core .

# Expose port 8080 for the application
EXPOSE 8080

# Set the entrypoint command to run the application using Gunicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
