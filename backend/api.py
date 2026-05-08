from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import re
from sqlglot import exp

from backend.llm_agent import ask_llm_to_fix
from backend.validator import SQLValidator

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ValidateRequest(BaseModel):
    sql: str
    schema_text: str 
    dialect: str="mysql"

@app.post("/api/validate")
async def validate_sql_endpoint(request: ValidateRequest):
    current_sql = request.sql
    history_logs = []
    issue_count = 0
    
    # --- LỚP PHÒNG THỦ 1: CHẶN RAW TEXT (Xử lý Typo như 'detele') ---
    forbidden_raw = ["delete", "update", "drop", "truncate", "alter", "detele", "updete"]
    if any(word in current_sql.lower() for word in forbidden_raw):
        return {
            "status": "failed", "issues": 1, "suggestions": 0, "final_ast": current_sql,
            "logs": ["❌ BỊ CHẶN: Phát hiện từ khóa nguy hiểm (DELETE/UPDATE...).", "🛑 Hệ thống dừng ngay lập tức!"]
        }

    # Phân tích Schema (ĐÃ VÁ LỖI THIẾU DẤU PHẨY)
    dynamic_schema, dynamic_restricted = SQLValidator.parse_schema_from_sql(
        request.schema_text,
        dialect=request.dialect
    )
    my_validator = SQLValidator(schema_dict=dynamic_schema, restricted_columns=dynamic_restricted)
    
    # Kiểm tra lần 1 (ĐÃ THÊM DIALECT)
    is_valid, result = my_validator.validate(current_sql, dialect=request.dialect)
    if is_valid:
        return {"status": "success", "issues": 0, "suggestions": 0, "final_ast": result, "logs": [f"✅ Thành công! SQL hợp lệ: {result}"]}

    # --- LỚP PHÒNG THỦ 2: CHẶN TỪ VALIDATOR MÀ KHÔNG CHO VÀO LOOP ---
    if "DELETE" in result.upper() or "UPDATE" in result.upper():
        return {
            "status": "failed", "issues": 1, "suggestions": 0, "final_ast": current_sql,
            "logs": [f"❌ Lỗi: {result}", "🛑 Thao tác bị cấm. Dừng xử lý!"]
        }

    issue_count += 1

    # VÒNG LẶP SỬA LỖI
    max_retries = 5
    for attempt in range(1, max_retries + 1):
        error_msg = result
        history_logs.append(f"❌ Lỗi: {error_msg}")

        # Lấy schema cho bảng
        target_table = None
        match = re.search(r"from\s+(\w+)", current_sql.lower())
        if match:
            target_table = match.group(1)
        
        available_columns = []
        if target_table in dynamic_schema:
            available_columns = [col for col in dynamic_schema[target_table].keys() if col not in dynamic_restricted]
        
        if "*" in current_sql or "SELECT *" in error_msg:
            error_msg = f"YÊU CẦU BẮT BUỘC: Thay '*' bằng các cột sau: {', '.join(available_columns)}"

        context_to_ai = json.dumps({target_table: dynamic_schema[target_table]} if target_table in dynamic_schema else dynamic_schema, indent=2)
        previous_sql = current_sql

        current_sql = ask_llm_to_fix(
            bad_sql=current_sql, 
            error_msg=error_msg, 
            schema_info=f"Cấu trúc bảng:\n{context_to_ai}", 
            restricted_info=f"Cấm dùng: {', '.join(dynamic_restricted)}",
            history=previous_sql,
            dialect=request.dialect
        )
        
        history_logs.append(f"🤖 AI sửa lần {attempt}: {current_sql}")

        # --- LỚP PHÒNG THỦ 3: CHẶN AI LÉN LÚT TẠO LỆNH DELETE/UPDATE ---
        if any(word in current_sql.lower() for word in forbidden_raw):
            history_logs.append("🛑 BỊ CHẶN: AI đã tạo ra lệnh thay đổi dữ liệu. Ép buộc dừng vòng lặp!")
            return {"status": "failed", "issues": issue_count + 1, "suggestions": attempt, "final_ast": current_sql, "logs": history_logs}
        
        # Validate lại câu SQL do AI viết (ĐÃ THÊM DIALECT)
        is_valid, result = my_validator.validate(current_sql, dialect=request.dialect)
        if is_valid:
            history_logs.append(f"✅ Thành công! SQL cuối cùng: {result}")
            return {"status": "fixed", "issues": issue_count, "suggestions": attempt, "final_ast": result, "logs": history_logs}
        else:
            # Nếu AI viết lệnh lỗi và lỗi đó là DELETE/UPDATE thì cũng văng luôn
            if "DELETE" in result.upper() or "UPDATE" in result.upper():
                history_logs.append(f"❌ Lỗi: {result}")
                history_logs.append("🛑 BỊ CHẶN: Phát hiện lệnh thay đổi dữ liệu. Ép buộc dừng!")
                return {"status": "failed", "issues": issue_count + 1, "suggestions": attempt, "final_ast": current_sql, "logs": history_logs}
            
            issue_count += 1

    history_logs.append("❌ THẤT BẠI: AI không thể tối ưu câu lệnh này.")
    return {"status": "failed", "issues": issue_count, "suggestions": max_retries, "final_ast": current_sql, "logs": history_logs}