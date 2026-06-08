#Lấy một máy tính ảo chạy Linux đã cài sẵn Python 3.11. Bản slim là bản rút gọn để cho nhẹ máy.
FROM python:3.11-slim 

# Tạo ra một thư mục tên là /app bên trong máy ảo đó. Mọi lệnh sau này đều diễn ra ở đây.
WORKDIR /app

# Cài thêm các bộ công cụ hệ thống (như libpq-dev để Python kết nối được với PostgreSQL).
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy file liệt kê thư viện từ máy tính của bạn vào trong máy ảo (dấu . nghĩa là vào thư mục /app).
COPY ./requirements.txt . 

# Tiến hành cài đặt các thư viện Python
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Bước 6: Copy toàn bộ mã nguồn từ thư mục backend ở máy thật vào container
COPY . .

# Bước 7: Mở cổng 8000 của container để FastAPI có thể đón nhận các request
EXPOSE 8000

# Bước 8: Lệnh mặc định để khởi chạy FastAPI bằng Uvicorn khi container bật lên
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]