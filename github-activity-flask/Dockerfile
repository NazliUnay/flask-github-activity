# Python 3.11 slim sürümünü baz alıyoruz
FROM python:3.11-slim

# Çalışma dizinini belirle
WORKDIR /app

# Önce requirements.txt'i kopyala
COPY requirements.txt requirements.txt

# Paketleri yükle
RUN pip install --no-cache-dir -r requirements.txt

# Tüm proje dosyalarını kopyala
COPY . .

# Flask uygulamasını dış IP'den erişilebilir yapıyoruz, port 5001'i açıyoruz
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5001

# Uygulamayı başlat
CMD ["python", "app.py"]
