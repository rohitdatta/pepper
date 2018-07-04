# Use Python 2.7 for pepper
FROM python:2.7

# Copy code to root directory of container
ADD . /app

# Set code directory to container work directory
WORKDIR /app

# Install python requirements
RUN pip install -r requirements.txt

# Open up external port
EXPOSE 5000

# Postgres connection config
ENV DATABASE_URL postgresql://postgres@postgres:5432/pepper

# Redis connection config
ENV REDIS_URL redis://redis:6379
