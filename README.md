# 🛡️ SQL Validator & Optimizer

Một hệ thống kiểm tra, tối ưu hóa và tự động sửa lỗi truy vấn SQL mạnh mẽ dựa trên **Cây cú pháp trừu tượng (AST)** và **Mô hình Ngôn ngữ Lớn (LLM)**. Dự án hỗ trợ đa hệ quản trị cơ sở dữ liệu và tích hợp các quy tắc bảo mật nghiêm ngặt.

## ✨ Tính năng nổi bật

- **🌍 Đa hệ quản trị CSDL (Multi-Dialect):** Hỗ trợ nhận diện và chuyển đổi cú pháp cho **MySQL**, **PostgreSQL**, và **SQL Server (T-SQL)** (Tự động chuyển `LIMIT` thành `TOP` đối với SQL Server).
- **🌳 Phân tích AST (Abstract Syntax Tree):** Sử dụng `sqlglot` để bóc tách và phân tích cấu trúc câu lệnh SQL ở mức độ sâu, đảm bảo độ chính xác tuyệt đối.
- **🔒 Bảo mật dữ liệu nhạy cảm:** Hỗ trợ thẻ ghi chú `-- sensitive` trong Database Schema để khóa vĩnh viễn quyền truy cập vào các cột nhạy cảm (VD: mật khẩu, ngày tháng quan trọng).
- **🛑 Lớp phòng thủ đa tầng:**
  - Ngăn chặn hoàn toàn các lệnh thay đổi dữ liệu nguy hiểm (`DELETE`, `UPDATE`, `DROP`, `TRUNCATE`, `ALTER`).
  - Cấm sử dụng `SELECT *` (Bắt buộc chỉ định rõ tên cột).
  - Bắt buộc phải có mệnh đề `LIMIT` (hoặc `TOP`) và giá trị phải `< 20` để chống quá tải server.
  - Bắt buộc mệnh đề `JOIN` phải đi kèm `ON` hoặc `USING`.
- **🤖 AI Auto-Fix:** LLM Agent tự động đọc lỗi từ Validator, kết hợp với Schema để tự động tối ưu và viết lại câu truy vấn chuẩn xác nhất.
- **🎨 Giao diện người dùng hiện đại:** Web UI được xây dựng bằng Tailwind CSS tinh gọn, mượt mà và trực quan.

## 📁 Cấu trúc thư mục

```text
SQLVALIDATOR/
│
├── backend/                # Logic xử lý chính (Python/FastAPI)
│   ├── __init__.py
│   ├── api.py              # API Server (FastAPI)
│   ├── llm_agent.py        # Module giao tiếp với AI (LLM)
│   └── validator.py        # Module bóc tách schema và validate AST
│
├── frontend/               # Giao diện người dùng (HTML/CSS/JS)
│   ├── css/
│   │   └── style.css       # File định dạng giao diện
│   ├── js/
│   │   └── app.js          # Logic kết nối API và xử lý UI
│   └── index.html          # Trang chủ Web UI
│
├── .env                    # Biến môi trường (API Keys) - Không đẩy lên Git
├── .gitignore              # Danh sách chặn file lên Git
├── requirements.txt        # Danh sách thư viện Python cần thiết
└── README.md               # Tài liệu hướng dẫn dự án

🚀 Hướng dẫn cài đặt
1. Yêu cầu hệ thống
Python 3.10 trở lên

Trình duyệt Web (Chrome, Edge, Firefox,...)

2. Cài đặt môi trường
Clone dự án về máy:

Bash
git clone [https://github.com/quangtuan-0210/SQLValidator.git](https://github.com/quangtuan-0210/SQLValidator.git)
cd SQLValidator
Tạo và kích hoạt môi trường ảo (Virtual Environment):

Bash
# Windows
python -m venv .venv
.\.venv\Scripts\activate

# MacOS/Linux
python3 -m venv .venv
source .venv/bin/activate
Cài đặt các thư viện phụ thuộc:

Bash
pip install -r requirements.txt
Thiết lập biến môi trường:
Tạo một file .env ở thư mục gốc và thêm API Key cho LLM của bạn (nếu có sử dụng API ngoài):

Đoạn mã
# Mẫu file .env
LLM_API_KEY=your_api_key_here
💻 Cách chạy dự án
Bước 1: Khởi động Backend Server
Mở Terminal, đảm bảo đã kích hoạt .venv và gõ lệnh:

Bash
uvicorn backend.api:app --reload
Server sẽ chạy tại: http://127.0.0.1:8000

Bước 2: Mở giao diện Frontend
Sử dụng Live Server trên VS Code để mở file frontend/index.html hoặc mở trực tiếp file này bằng trình duyệt của bạn.