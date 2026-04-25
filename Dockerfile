# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the pyproject.toml file and install dependencies
# This layer is cached to speed up builds if dependencies don't change
COPY pyproject.toml .
RUN pip install .

# Copy the rest of the application's source code
COPY annex4/ ./annex4/

# Specify the entrypoint for the container
ENTRYPOINT ["annex4-cli"]

# Default command can be --help
CMD ["--help"]
