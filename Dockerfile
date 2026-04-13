FROM python:3.11-slim

# ── 1. Tizim kutubxonalari ─────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget curl unzip ca-certificates \
    fonts-liberation libasound2 libatk-bridge2.0-0 libatk1.0-0 \
    libcairo2 libcups2 libdbus-1-3 libexpat1 libfontconfig1 libgbm1 \
    libglib2.0-0 libgtk-3-0 libnspr4 libnss3 libpango-1.0-0 \
    libstdc++6 libx11-6 libx11-xcb1 libxcb1 libxcomposite1 libxcursor1 \
    libxdamage1 libxext6 libxfixes3 libxi6 libxrandr2 libxrender1 \
    libxss1 libxtst6 xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# ── 2. Google Chrome — to'g'ridan .deb orqali (apt-key ishlatilmaydi) ─────────
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get update \
    && apt-get install -y ./google-chrome-stable_current_amd64.deb \
    && rm google-chrome-stable_current_amd64.deb \
    && rm -rf /var/lib/apt/lists/*

# ── 3. ChromeDriver — Chrome versiyasiga mos ──────────────────────────────────
RUN CHROME_VER=$(google-chrome --version | grep -oP '\d+' | head -1) \
    && CDV=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VER}") \
    && wget -q "https://chromedriver.storage.googleapis.com/${CDV}/chromedriver_linux64.zip" \
    && unzip chromedriver_linux64.zip \
    && mv chromedriver /usr/local/bin/chromedriver \
    && chmod +x /usr/local/bin/chromedriver \
    && rm chromedriver_linux64.zip

# ── 4. Python ilovasi ──────────────────────────────────────────────────────────
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py database.py selenium_handler.py ./

RUN mkdir -p /app/data

CMD ["python", "bot.py"]