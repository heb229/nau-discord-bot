# 1. use official Python image
FROM python:3.11-slim

# 2. Set working directory
WORKDIR /app

# 3. Copy dependency file
COPY requirements.txt .

# 4. Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of the project
COPY . .

# 6. Run the app
CMD ["python", "bot.py"]