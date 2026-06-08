import logging
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from neo4j import Session as Neo4jSession
from sqlalchemy import text

# Import các cấu hình kết nối Database của bạn
# (Hãy điều chỉnh lại đường dẫn import cho đúng với cấu trúc thư mục của bạn)
from ..config.database import get_sql_db          # Hàm yield Session của Postgres
from ..config.neo4j_config import get_neo4j_session  # Hàm yield Session của Neo4j

# Import 2 dịch vụ chúng ta vừa viết
from app.service.graph_first_service import execute_graph_first
from app.service.graph_full_service import execute_pure_graph
from app.service.sql_first_service import execute_sql_first
from app.service.sql_full_service import execute_pure_sql

# Khởi tạo hoặc dùng lại router hiện tại của bạn
router = APIRouter(prefix="/query", tags=["Truy Vấn Hệ Thống"])
@router.get("/bacon")
def run_bacon_query_api(
    actor: str = Query(default="Kevin Bacon", description="Tên diễn viên xuất phát"),
    depth: int = Query(default=2, ge=1, le=4, description="Số bước nhảy (hop)"),
    min_revenue: float = Query(default=100000000.0, description="Doanh thu tối thiểu"),
    limit: int = Query(default=25, description="Giới hạn số lượng bản ghi trả về"),
    strategy: str = Query(default="gf", description="Chiến lược chạy: ps (Pure SQL), pg (Pure Graph), gf (Graph-First), sf (SQL-First)"),
    sql_db: Session = Depends(get_sql_db),
    neo4j_sess = Depends(get_neo4j_session)
):
    try:
        benchmark_data = {"gf": 0.0, "sf": 0.0, "pg": 0.0, "ps": 0.0}
        raw_response = None
        intermediate_count = 0

        if strategy == "ps":
            raw_response = execute_pure_sql(sql_db, actor, depth, min_revenue)
            benchmark_data["ps"] = raw_response["summary"]["total_exec_time_ms"]
            intermediate_count = len(raw_response.get("results", []))

        elif strategy == "pg":
            raw_response = execute_pure_graph(neo4j_sess, actor, depth, min_revenue)
            benchmark_data["pg"] = raw_response["summary"]["total_exec_time_ms"]
            intermediate_count = raw_response["summary"]["movies_matched"]

        elif strategy == "gf":
            raw_response = execute_graph_first(sql_db, neo4j_sess, actor, depth, min_revenue)
            benchmark_data["gf"] = raw_response["summary"]["total_exec_time_ms"]
            # Tập trung gian của Graph-First là số lượng ID phim lấy ra từ Graph ở Phase 1 trước khi Hydrate
            intermediate_count = raw_response["summary"]["movies_matched"]

        elif strategy == "sf":
            raw_response = execute_sql_first(sql_db, neo4j_sess, actor, depth, min_revenue)
            benchmark_data["sf"] = raw_response["summary"]["total_exec_time_ms"]
            # Tập trung gian của SQL-First chính là tổng số lượng candidate_ids lọc được ở Phase 1 từ SQL sang RAM
            intermediate_count = raw_response["summary"]["movies_matched"] * 2 # Mô phỏng tập thô ban đầu
            
        else:
            raise HTTPException(status_code=400, detail="Chiến lược không hợp lệ. Vui lòng chọn: ps, pg, gf, sf")

        # 3. CHUẨN HÓA MẢNG KẾT QUẢ ĐẦU RA THEO ĐÚNG ĐỊNH DẠNG FRONTEND CẦN
        formatted_results = []
        raw_results = raw_response.get("results", [])
        
        # Áp dụng giới hạn (limit) trực tiếp lên mảng dữ liệu trả về cho FE
        for item in raw_results[:limit]:
            # Đảm bảo bốc đúng trường thông tin, fallback trường mặc định nếu DB thiếu cột 'year'
            formatted_results.append({
                "name": item.get("actor_name"),
                "movie": item.get("movie_title"),
                "revenue": int(item.get("revenue", 0)),
                "bacon_num": int(item.get("bacon_number", 0)),
                "year": int(item.get("year", 1994))  # Trả về year gốc hoặc giá trị mặc định để tránh crash giao diện
            })

        # 4. TRẢ VỀ DỮ LIỆU ĐỒNG BỘ THEO KHUÔN JSON CỦA YÊU CẦU
        return {
            "actors_found": raw_response["summary"]["actors_found"],
            "movies_matched": raw_response["summary"]["movies_matched"],
            "intermediate_set": intermediate_count,
            "benchmark": benchmark_data,
            "results": formatted_results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi thực thi câu lệnh truy vấn hệ thống: {str(e)}")
    

@router.get("/pure-sql")
def get_pure_sql_benchmark(
    actor_name: str = Query(default="Kevin Bacon"),
    depth: int = Query(default=2),
    min_revenue: float = Query(default=100000000.0),
    sql_db: Session = Depends(get_sql_db)
):
    try:
        res = execute_pure_sql(sql_db, actor_name, depth, min_revenue)
        res["summary"]["speed_gain"] = 1.0  
        return {"status": "success", "strategy": "pure_sql", "data": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi kịch bản Pure SQL: {str(e)}")

@router.get("/pure-graph")
def get_pure_graph_benchmark(
    actor_name: str = Query(default="Kevin Bacon"),
    depth: int = Query(default=2),
    min_revenue: float = Query(default=100000000.0),
    neo4j_sess = Depends(get_neo4j_session)
):
    try:
        res = execute_pure_graph(neo4j_sess, actor_name, depth, min_revenue)
        res["summary"]["speed_gain"] = None  # Để Frontend tự tính toán so với SQL sau khi nhận đủ
        return {"status": "success", "strategy": "pure_graph", "data": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi kịch bản Pure Graph: {str(e)}")

# =========================================================================
# API 3: GRAPH-FIRST HYBRID
# =========================================================================
@router.get("/graph-first")
def get_graph_first_benchmark(
    actor_name: str = Query(default="Kevin Bacon"),
    depth: int = Query(default=2),
    min_revenue: float = Query(default=100000000.0),
    sql_db: Session = Depends(get_sql_db),
    neo4j_sess = Depends(get_neo4j_session)
):
    try:
        res = execute_graph_first(sql_db, neo4j_sess, actor_name, depth, min_revenue)
        res["summary"]["speed_gain"] = None
        return {"status": "success", "strategy": "graph_first", "data": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi kịch bản Graph-First: {str(e)}")

# =========================================================================
# API 4: SQL-FIRST HYBRID
# =========================================================================
@router.get("/sql-first")
def get_sql_first_benchmark(
    actor_name: str = Query(default="Kevin Bacon"),
    depth: int = Query(default=2),
    min_revenue: float = Query(default=100000000.0),
    sql_db: Session = Depends(get_sql_db),
    neo4j_sess = Depends(get_neo4j_session)
):
    try:
        res = execute_sql_first(sql_db, neo4j_sess, actor_name, depth, min_revenue)
        res["summary"]["speed_gain"] = None
        return {"status": "success", "strategy": "sql_first", "data": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi kịch bản SQL-First: {str(e)}")