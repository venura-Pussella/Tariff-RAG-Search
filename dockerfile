# Mentioning amd64 specifically cuz on the mac it defaulted to arm64 and failed in the Azure container (if I pushed this image directly)
# FROM --platform=linux/amd64 python:3.11-slim-bookworm
FROM python:3.11-slim-bookworm

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install -r requirements.txt

# Expose port 80 for Azure
EXPOSE 80

# Run main.py when the container launches
ENTRYPOINT ["gunicorn", "--bind=0.0.0.0:80", "--workers=1", "--threads=4", "app:app"]

# docker build -t tariff_search .
# docker run -p 8000:8000 tariff_search