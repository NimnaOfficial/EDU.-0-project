FROM python:3.11-slim

# 1. Install System Dependencies (Running as ROOT)
RUN apt-get update && apt-get install -y \
  libreoffice-core \
  libreoffice-impress \
  --no-install-recommends \
  && rm -rf /var/lib/apt/lists/* # Cleans up cache to keep image small!

# 2. Create the secure bot user
RUN adduser --disabled-password --gecos "" eduuser

# 3. Set the working directory
WORKDIR /app

# 4. Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy your bot's source code
COPY ./app .

# 6. Switch to the secure user right before running the bot
USER eduuser

# 7. Start the engine
CMD ["python", "main.py"]