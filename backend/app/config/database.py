from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError
import os 
import urllib.parse
from contextlib import contextmanager
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "Thuc2022005@")
DB_HOST = os.getenv("POSTGRES_HOST", "127.0.0.1")
# DB_HOST = os.getenv("POSTGRES_HOST", "movie_postgres_container")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "movie_data")
safe_password = urllib.parse.quote_plus(DB_PASSWORD)
# Định dạng URL kết nối PostgreSQL
DATABASE_URL = f"postgresql://{DB_USER}:{safe_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(
    DATABASE_URL, 
    pool_size=10, 
    max_overflow=20,
    pool_pre_ping=True, # Tự động kiểm tra kết nối còn sống hay không trước khi truy vấn
    # connect_args={"host": "127.0.0.1"}
)
try:
    # Tạo một kết nối ngắn hạn để kiểm tra (ping)
    with engine.connect() as connection:
        # Gửi lệnh SQL nguyên bản SELECT 1 để test phản hồi của DB
        connection.execute(text("SELECT 1"))
    print("🚀 [SUCCESS] Kết nối đến PostgreSQL thành công! Sẵn sàng làm việc.")
except OperationalError as e:
    print("[ERROR] Kết nối đến PostgreSQL thất bại!")
    print(f"Chi tiết lỗi: {e}")

# Khởi tạo Session factory để tạo phiên làm việc với DB
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Base class để định nghĩa các Model (bảng) dữ liệu sau này
Base = declarative_base()

# Dependency dùng cho các Endpoint của FastAPI (Context Manager)
def get_sql_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()