# Cross-Model Query Lab 🔗

> **Tối ưu hóa Truy vấn Đa mô hình Liên kết Neo4j - PostgreSQL**  
> Phát triển bởi: **Phạm Nguyễn Minh Thức** & Cộng sự

Hệ thống thực thi và tối ưu hóa truy vấn liên mô hình (Cross-Model Join Optimization) kết hợp Neo4j và PostgreSQL, cho phép đo lường chi phí I/O và chi phí truyền tải dựa trên framework lý thuyết của Özsu & Valduriez.

---

## 📋 Mục lục

- [Tổng quan](#-tổng-quan)
- [Cấu trúc thư mục](#-cấu-trúc-thư-mục)
- [Yêu cầu hệ thống](#-yêu-cầu-hệ-thống)
- [Cài đặt](#-cài-đặt)
- [Cấu hình môi trường](#-cấu-hình-môi-trường)
- [Khởi chạy hệ thống](#-khởi-chạy-hệ-thống)
- [API Endpoints](#-api-endpoints)
- [Ghi chú kỹ thuật](#️-ghi-chú-kỹ-thuật)

---

## 🧠 Tổng quan

Kho lưu trữ này chứa toàn bộ mã nguồn của hệ thống tối ưu hóa truy vấn liên mô hình. Hệ thống:

- Kết hợp **Neo4j** (lưu trữ đồ thị quan hệ đa tầng) và **PostgreSQL** (lọc dữ liệu có cấu trúc khối lượng lớn)
- Cung cấp giao diện **Lab trực quan** để cấu hình động các bài toán thực nghiệm
- Đo lường **chi phí I/O** (Rows scanned) và **chi phí truyền tải** (Intermediate set size)
- Hỗ trợ hai chiến lược tối ưu: **Graph-First Join** và **SQL-First Join**

---

## 📁 Cấu trúc thư mục

```
cross-model-query-lab/
│
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI endpoints chính
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── postgres.py             # Kết nối Engine & Session SQLAlchemy
│   │   └── neo4j_db.py             # Quản lý Driver kết nối Native Neo4j
│   │
│   └── service/
│       ├── __init__.py
│       ├── graph_first_service.py  # Logic chiến lược Graph-First Join
│       └── sql_first_service.py    # Logic chiến lược SQL-First Join
│
├── frontend/
│   └── cross_model_query.html      # Dashboard Lab giám sát & trực quan hóa
│
├── requirements.txt                # Danh sách thư viện phụ thuộc Python
├── .env                            # Biến môi trường cấu hình kết nối
└── README.md
```

---

## ⚙️ Yêu cầu hệ thống

| Thành phần | Phiên bản tối thiểu |
|---|---|
| Python | 3.9+ |
| PostgreSQL | 15+ |
| Neo4j | 5+ |

### Cấu hình cơ sở dữ liệu

**PostgreSQL:** Tạo database `cinema_db` với bảng `box_office_revenue` gồm các cột:
- `movie_id` (PK), `title`, `revenue`
- `is_small`, `is_medium` (boolean — phục vụ phân mảnh)

**Neo4j:** Kích hoạt DBMS và gán nhãn dữ liệu với tiền tố phân mảnh động:
- Nút diễn viên: `:Actor:Small`, `:Actor:Medium`, `:Actor:Large`
- Nút phim: `:Movie:Small`, `:Movie:Medium`, `:Movie:Large`

---

## 🚀 Cài đặt

### 1. Clone repository

```bash
git clone https://github.com/<your-username>/cross-model-query-lab.git
cd cross-model-query-lab
```

### 2. Tạo và kích hoạt môi trường ảo

```bash
# Tạo môi trường ảo
python -m venv venv

# Kích hoạt trên Windows
.\venv\Scripts\activate

# Kích hoạt trên Linux/macOS
source venv/bin/activate
```

### 3. Cài đặt thư viện phụ thuộc

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**Nội dung `requirements.txt`:**

```
fastapi>=0.100.0
uvicorn>=0.22.0
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.6
neo4j>=5.10.0
python-dotenv>=1.0.0
pandas>=2.0.0
```

---

## 🔧 Cấu hình môi trường

Tạo file `.env` tại thư mục gốc (cùng cấp với `requirements.txt`):

```env
# Chuỗi kết nối PostgreSQL
DATABASE_URL=postgresql://postgres:password123@localhost:5432/cinema_db

# Thông tin xác thực Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password123
```

> ⚠️ **Lưu ý:** Thay `password123` bằng mật khẩu thực tế của bạn. Không commit file `.env` lên Git.

---

## ▶️ Khởi chạy hệ thống

### Bước 1 — Khởi động cơ sở dữ liệu

Đảm bảo PostgreSQL và Neo4j đang **Active** và lắng nghe đúng cổng:
- PostgreSQL: `5432`
- Neo4j: `7687`

### Bước 2 — Khởi chạy FastAPI Backend

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Khi log terminal hiển thị `Application startup complete.`, server đã sẵn sàng tại `http://127.0.0.1:8000`.

### Bước 3 — Mở Dashboard

Mở file `frontend/cross_model_query.html` bằng trình duyệt (Chrome, Edge, Firefox).

Nếu ô trạng thái hiển thị **⬤ API connected** (màu xanh) → hệ thống đã sẵn sàng thực thi.

---

## 📡 API Endpoints

### `GET /query/bacon` — Truy vấn chéo đơn lẻ

Thực hiện phép ghép nối liên mô hình với các tham số:

| Tham số | Mô tả |
|---|---|
| `actor` | Tên diễn viên khởi đầu |
| `depth` | Độ sâu duyệt đồ thị |
| `min_revenue` | Ngưỡng doanh thu tối thiểu (PostgreSQL filter) |
| `strategy` | `graph_first` hoặc `sql_first` |
| `dataset_size` | `small`, `medium`, hoặc `large` |

### `GET /benchmark/bacon` — Benchmarking tự động

Kích hoạt vòng lặp chạy N lần liên tiếp, tính toán các giá trị thống kê học thuật:
- **Mean**, **Std** (độ lệch chuẩn), **P95** (phân vị thứ 95)

Kết quả dùng để vẽ biểu đồ so sánh hiệu năng hai chiến lược.

---

## 🛠️ Ghi chú kỹ thuật

Một số lỗi đã được phát hiện và xử lý trong quá trình phát triển:

**So sánh chuỗi phân mảnh từ Frontend**
Backend sử dụng `.startswith('small')` thay vì so sánh tuyệt đối `== 'small'` để tránh lỗi lọt điều kiện do chuỗi gửi lên chứa text phụ như `'Small (200)'`. Ngăn SQL-First chạy nhầm sang Full Table Scan trên tập Large.

**Crash bộ nhớ `tracemalloc`**
Đã loại bỏ việc gọi trùng lặp `tracemalloc.stop()`. Lệnh tắt chỉ được gọi một lần duy nhất tại khối tổng kết, triệt tiêu `RuntimeError` khi chạy Benchmark nhiều lần.

**Path Explosion trong Cypher**
Câu lệnh Cypher đã được tối ưu bằng cách thêm `WITH DISTINCT co_actor, a` trước khi gọi `shortestPath`, loại bỏ các luồng lặp thừa và bảo vệ bộ nhớ RAM khỏi quá tải.

---

## 📄 License

Dự án này được phát triển cho mục đích học thuật trong khuôn khổ đồ án tốt nghiệp.