# test_api.py
import requests
import json

# Định nghĩa địa chỉ API cần test
URL = "http://localhost:8000/query/bacon"
PARAMS = {
    "actor": "Kevin Bacon",
    "depth": 2,
    "min_revenue": 100000000.0,
    "limit": 5,
    "strategy": "gf"  # Đổi thành 'sf', 'ps', 'pg' để test các chiến lược khác
}

print("🚀 Đang gửi request test tới API Backend...")

try:
    # Thực hiện gọi API qua giao thức GET
    response = requests.get(URL, params=PARAMS)
    
    # Kiểm tra mã trạng thái trả về
    print(f"Trạng thái HTTP: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ Kết nối thành công! Cấu trúc dữ liệu nhận được:")
        # Ép định dạng JSON có lùi dòng (indent) để hiển thị đẹp mắt trên Console
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    else:
        print(f"❌ API trả về lỗi: {response.text}")

except Exception as e:
    print(f"💥 Không thể kết nối tới Server FastAPI: {str(e)}")
    print("Vui lòng đảm bảo bạn đã chạy lệnh 'uvicorn app.main:app --reload' trước!")