import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError, OptimizeError
import re

class SQLValidator:
    @staticmethod
    def parse_schema_from_sql(schema_text: str, dialect: str = "mysql"):
        dynamic_schema = {}
        dynamic_restricted = []

        if not schema_text or schema_text.strip() == "":
            return dynamic_schema, dynamic_restricted

        # 1. QUÉT TÌM CỘT SENSITIVE 
        for line in schema_text.split('\n'):
            if "-- sensitive" in line.lower():
                match = re.search(r"^\s*[`\"\[]?([a-zA-Z0-9_]+)", line)
                if match:
                    col_name = match.group(1).lower()
                    if col_name not in dynamic_restricted:
                        dynamic_restricted.append(col_name)

        # 2. TẨY RỬA COMMENT
        cleaned_text = re.sub(r"--.*", "", schema_text)

        # 3. TRÍCH XUẤT CẤU TRÚC (THUẬT TOÁN CHẺ CHUỖI AN TOÀN TUYỆT ĐỐI)
        # Cắt các bảng ra thành từng khối riêng biệt dựa vào chữ CREATE TABLE
        blocks = re.split(r"(?i)CREATE\s+TABLE\s+", cleaned_text)
        
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            
            # Tìm vị trí mở ngoặc đầu tiên và đóng ngoặc cuối cùng của bảng
            start_idx = block.find('(')
            end_idx = block.rfind(')')
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                # Cắt lấy tên bảng
                table_name = block[:start_idx].strip(' `\"[]').lower()
                dynamic_schema[table_name] = {}
                
                # Cắt lấy phần lõi định nghĩa các cột
                columns_str = block[start_idx+1 : end_idx]
                
                # Xóa sạch các ngoặc của data type (VD: DECIMAL(10,2) -> DECIMAL)
                # Bước này giúp ta thoải mái chẻ tiếp bằng dấu phẩy mà không sợ lỗi
                safe_columns_str = re.sub(r"\([^)]*\)", "", columns_str)
                
                # Chẻ từng dòng cột bằng dấu phẩy
                for col_def in safe_columns_str.split(','):
                    col_def = col_def.strip()
                    if not col_def or col_def.upper().startswith(('PRIMARY', 'FOREIGN', 'UNIQUE', 'CONSTRAINT')):
                        continue
                        
                    parts = col_def.split()
                    if len(parts) >= 2:
                        col_name = parts[0].strip('`"[]').lower()
                        if col_name not in ('primary', 'foreign', 'constraint', 'unique', 'key'):
                            col_type = parts[1].upper()
                            dynamic_schema[table_name][col_name] = col_type

        print("\n" + "=" * 50)
        print(f"🔒 [SECURITY] CÁC CỘT BỊ CẤM: {dynamic_restricted}")
        print("🔍 [DEBUG] DICTIONARY BẢNG ĐÃ NẠP:")
        print(dynamic_schema)
        print("=" * 50 + "\n")

        return dynamic_schema, dynamic_restricted

    def __init__(self, schema_dict, restricted_columns=None, restricted_row_values=None):
        self.schema_dict = {t: {c.lower() for c in cols} for t, cols in schema_dict.items()}
        self.restricted_columns = [c.lower() for c in (restricted_columns or [])]
        self.restricted_row_values = restricted_row_values or {}

    def validate(self, sql_text, dialect: str = "mysql"):
        try:
            ast = sqlglot.parse_one(sql_text, read=dialect)
            self._validate_rules(ast)
            self._validate_columns(ast)
            self._validate_joins(ast)
            return True, ast.sql(dialect=dialect)
        except (ParseError, OptimizeError, ValueError) as e:
            return False, str(e)

    def _validate_rules(self, ast):
        if isinstance(ast, (exp.Delete, exp.Update)):
            raise ValueError("Rule Violation: Các thao tác DELETE và UPDATE không được phép.")
        
        if isinstance(ast, exp.Select):
            if ast.find(exp.Star):
                raise ValueError("Rule Violation: Không được phép sử dụng 'SELECT *'. Hãy chỉ định rõ các cột.")
            
            limit_node = ast.args.get("limit")
            if not limit_node:
                raise ValueError("Rule Violation: Truy vấn SELECT bắt buộc phải có LIMIT.")
            
            # --- BẢN VÁ LỖI: TÁCH RIÊNG PHẦN TRY-EXCEPT ---
            limit_val = None
            try:
                # Chỉ dùng try-except để bắt lỗi khi cố gắng bóc tách con số
                limit_val = int(limit_node.expression.this)
            except:
                pass
            
            # Đưa lệnh kiểm tra ra ngoài. Nếu vượt quá 20 thì ném lỗi mà KHÔNG BỊ BỊT MIỆNG
            if limit_val is not None and limit_val >= 20:
                raise ValueError(f"Rule Violation: LIMIT phải < 20. Đang yêu cầu: {limit_val}.")

        for col in ast.find_all(exp.Column):
            if col.name.lower() in self.restricted_columns:
                raise ValueError(f"Rule Violation: Không có quyền truy cập cột bảo mật '{col.name}'.")

    def _validate_columns(self, ast):
        if not self.schema_dict:
            raise ValueError("Schema Validation: Hệ thống chưa nạp được Database Schema. Vui lòng kiểm tra lại cấu trúc bảng.")

        tables_in_query = set()
        for table_node in ast.find_all(exp.Table):
            tables_in_query.add(table_node.name.lower())

        valid_columns = set()
        for t in tables_in_query:
            if t in self.schema_dict:
                valid_columns |= self.schema_dict[t]
            else:
                raise ValueError(f"Table Validation: Bảng '{t}' không tồn tại trong Schema.")

        for col in ast.find_all(exp.Column):
            col_name = col.name.lower()
            if col_name and col_name not in valid_columns:
                raise ValueError(f"Column Validation: Cột '{col.name}' không tồn tại. Các cột hợp lệ: {', '.join(sorted(valid_columns))}")

    def _validate_joins(self, ast):
        for join in ast.find_all(exp.Join):
            if not join.args.get("on") and not join.args.get("using"):
                raise ValueError("Join Validation: Bắt buộc phải có mệnh đề 'ON' hoặc 'USING' khi JOIN.")



#gom hết vào thành 1 block rồi sửa 1 lần
'''
def validate(self, sql_text, dialect: str = "mysql"):
        try:
            ast = sqlglot.parse_one(sql_text, read=dialect)
            
            # Tạo một cái "giỏ" để gom tất cả các lỗi lại
            all_errors = []
            
            # Thu thập lỗi từ mọi mặt trận thay vì dừng lại giữa chừng
            all_errors.extend(self._validate_rules(ast))
            all_errors.extend(self._validate_columns(ast))
            all_errors.extend(self._validate_joins(ast))
            
            # Nếu giỏ có chứa lỗi, gộp chúng lại thành 1 chuỗi dài và báo False
            if all_errors:
                # Mỗi lỗi nằm trên 1 dòng để AI dễ đọc
                return False, "\n- ".join(["Có nhiều lỗi cần sửa cùng lúc:"] + all_errors)
                
            return True, ast.sql(dialect=dialect)
        except (ParseError, OptimizeError) as e:
            return False, f"Lỗi cú pháp SQL: {str(e)}"
        except ValueError as e:
            # Vẫn giữ lại ValueError cho các lỗi hệ thống nghiêm trọng
            return False, str(e)

    def _validate_rules(self, ast):
        errors = []
        if isinstance(ast, (exp.Delete, exp.Update)):
            errors.append("Rule Violation: Các thao tác DELETE và UPDATE không được phép.")
        
        if isinstance(ast, exp.Select):
            if ast.find(exp.Star):
                errors.append("Rule Violation: Không được phép sử dụng 'SELECT *'. Hãy chỉ định rõ các cột.")
            
            limit_node = ast.args.get("limit")
            if not limit_node:
                errors.append("Rule Violation: Truy vấn SELECT bắt buộc phải có LIMIT hoặc TOP.")
            
            limit_val = None
            try:
                limit_val = int(limit_node.expression.this)
            except:
                pass
            
            if limit_val is not None and limit_val >= 20:
                errors.append(f"Rule Violation: LIMIT/TOP phải < 20. Đang yêu cầu: {limit_val}.")

        for col in ast.find_all(exp.Column):
            if col.name.lower() in self.restricted_columns:
                errors.append(f"Rule Violation: Không có quyền truy cập cột bảo mật '{col.name}'.")
                
        return errors # Trả về danh sách lỗi thay vì raise

    def _validate_columns(self, ast):
        errors = []
        if not self.schema_dict:
            raise ValueError("Schema Validation: Hệ thống chưa nạp được Database Schema. Vui lòng kiểm tra lại cấu trúc bảng.")

        tables_in_query = set()
        for table_node in ast.find_all(exp.Table):
            tables_in_query.add(table_node.name.lower())

        valid_columns = set()
        for t in tables_in_query:
            if t in self.schema_dict:
                valid_columns |= self.schema_dict[t]
            else:
                errors.append(f"Table Validation: Bảng '{t}' không tồn tại trong Schema.")

        for col in ast.find_all(exp.Column):
            col_name = col.name.lower()
            if col_name and col_name not in valid_columns:
                errors.append(f"Column Validation: Cột '{col.name}' không tồn tại. Các cột hợp lệ: {', '.join(sorted(valid_columns))}")
                
        return errors # Trả về danh sách lỗi

    def _validate_joins(self, ast):
        errors = []
        for join in ast.find_all(exp.Join):
            if not join.args.get("on") and not join.args.get("using"):
                errors.append("Join Validation: Bắt buộc phải có mệnh đề 'ON' hoặc 'USING' khi JOIN.")
        return errors # Trả về danh sách lỗi
'''
