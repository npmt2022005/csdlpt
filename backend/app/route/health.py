import logging
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

# Import các cấu hình kết nối Database của bạn
# (Hãy điều chỉnh lại đường dẫn import cho đúng với cấu trúc thư mục của bạn)
from ..config.database import get_sql_db          # Hàm yield Session của Postgres
from ..config.neo4j_config import get_neo4j_session  # Hàm yield Session của Neo4j


health_router = APIRouter(tags=["Kiểm Tra Hệ Thống"])

@health_router.get("/health")
def check_system_health(
    sql_db: Session = Depends(get_sql_db),
    neo4j_sess = Depends(get_neo4j_session)
):
    postgres_alive = False
    neo4j_alive = False
    
    pg_rows_display = "0 rows"
    neo4j_nodes_display = "0 nodes"

    try:
        sql_db.execute(text("SELECT 1"))
        postgres_alive = True
        
        query_fast_count = text("""
            SELECT reltuples::bigint 
            FROM pg_class 
            WHERE relname = 'box_office_revenue'
        """)
        row_count_res = sql_db.execute(query_fast_count).scalar()
        
        if row_count_res and row_count_res >= 1_000_000:
            pg_rows_display = f"{round(row_count_res / 1_000_000, 1)}M rows"
        elif row_count_res:
            pg_rows_display = f"{row_count_res:,} rows"
            
    except Exception as pg_err:
        logging.error(f"PostgreSQL Health Check Failed: {str(pg_err)}")
        postgres_alive = False
        pg_rows_display = "Unavailable"

    # 2. KIỂM TRA NEO4J GRAPH DB
    try:
        neo4j_res = neo4j_sess.run("MATCH (n) RETURN count(n) AS total_nodes")
        single_record = neo4j_res.single()
        
        if single_record:
            node_count = single_record["total_nodes"]
            neo4j_alive = True
            
            if node_count >= 1_000_000:
                neo4j_nodes_display = f"{round(node_count / 1_000_000, 1)}M nodes"
            else:
                neo4j_nodes_display = f"{node_count:,} nodes"
                
    except Exception as neo_err:
        logging.error(f"Neo4j Health Check Failed: {str(neo_err)}")
        neo4j_alive = False
        neo4j_nodes_display = "Unavailable"

    # 3. ĐÓNG GÓI JSON ĐÚNG CHUẨN FRONTEND YÊU CẦU
    return {
        "version": "1.0",
        "neo4j": neo4j_alive,
        "neo4j_nodes": neo4j_nodes_display,
        "postgres": postgres_alive,
        "pg_rows": pg_rows_display
    }
