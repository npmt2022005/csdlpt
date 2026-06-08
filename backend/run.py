import json
import os
import sys
# Bổ sung đường dẫn hệ thống để Python tìm thấy package app nếu cần
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine


from app.config.database import get_sql_db
from app.config.neo4j_config import get_neo4j_session   
from app.service.graph_first_service import execute_graph_first
from app.service.graph_full_service import execute_pure_graph
from app.service.sql_first_service import execute_sql_first
from app.service.sql_full_service import execute_pure_sql

def run_comprehensive_benchmark():
    print("=" * 70)
    print(" KHỞI CHẠY HỆ THỐNG TEST BENCHMARK ĐỐI CHỨNG 4 CHIẾN LƯỢC ")
    print("=" * 70)

    # Cấu hình tham số thực nghiệm
    actor_target = "Kevin Bacon"
    depth_hops = 2
    min_revenue_threshold = 100000000.0

    print(f"Tham số: {actor_target} | Depth: {depth_hops} | Revenue: {min_revenue_threshold:,} USD\n")

    sql_gen = get_sql_db()
    neo4j_gen = get_neo4j_session()

    sql_db = next(sql_gen)
    neo4j_sess = next(neo4j_gen)

    try:
        # -----------------------------------------------------------------
        # Kịch bản 1: Pure SQL (Baseline)
        # -----------------------------------------------------------------
        print("-> Đang chạy: Pure SQL (Recursive CTE)...")
        res_pure_sql = execute_pure_sql(sql_db, actor_target, depth_hops, min_revenue_threshold)

        # -----------------------------------------------------------------
        # Kịch bản 2: Pure Graph
        # -----------------------------------------------------------------
        print("-> Đang chạy: Pure Graph (Cypher Only)...")
        res_pure_graph = execute_pure_graph(neo4j_sess, actor_target, depth_hops, min_revenue_threshold)

        # -----------------------------------------------------------------
        # Kịch bản 3: Graph-First Hybrid
        # -----------------------------------------------------------------
        print("-> Đang chạy: Graph-First (Hybrid 3-Phase)...")
        res_graph_first = execute_graph_first(sql_db, neo4j_sess, actor_target, depth_hops, min_revenue_threshold)

        # -----------------------------------------------------------------
        # Kịch bản 4: SQL-First Hybrid
        # -----------------------------------------------------------------
        print("-> Đang chạy: SQL-First (Hybrid 3-Phase)...")
        res_sql_first = execute_sql_first(sql_db, neo4j_sess, actor_target, depth_hops, min_revenue_threshold)

        base_time = max(res_pure_sql["summary"]["total_exec_time_ms"], 0.001)
        
        res_pure_graph["summary"]["speed_gain"] = round(base_time / max(res_pure_graph["summary"]["total_exec_time_ms"], 0.001), 2)
        res_graph_first["summary"]["speed_gain"] = round(base_time / max(res_graph_first["summary"]["total_exec_time_ms"], 0.001), 2)
        res_sql_first["summary"]["speed_gain"] = round(base_time / max(res_sql_first["summary"]["total_exec_time_ms"], 0.001), 2)

        # Đóng gói cấu trúc tổng hợp xuất file JSON
        complete_output = {
            "pure_sql": res_pure_sql,
            "pure_graph": res_pure_graph,
            "graph_first": res_graph_first,
            "sql_first": res_sql_first
        }
        print(len(res_pure_sql.get("results", [])))
        print(len(res_pure_graph.get("results", [])))
        print(len(res_graph_first.get("results", [])))
        print(len(res_sql_first.get("results", [])))
        # # =================================================================
        # # IN BẢNG BÁO CÁO HIỆU NĂNG RA TERMINAL
        # # =================================================================
        # print("\n" + "=" * 70)
        # print(" BẢNG KẾT QUẢ SO SÁNH HIỆU NĂNG (BENCHMARK REPORT) ")
        # print("=" * 70)
        # print(f"{'Chiến lược thực thi':<28} | {'Tổng thời gian':<15} | {'Speed Gain':<12}")
        # print("-" * 70)
        # print(f"{'Pure SQL (Recursive CTE)':<28} | {res_pure_sql['summary']['total_exec_time_ms']:>10} ms | {res_pure_sql['summary']['speed_gain']:>10}x")
        # print(f"{'Pure Graph (Cypher Only)':<28} | {res_pure_graph['summary']['total_exec_time_ms']:>10} ms | {res_pure_graph['summary']['speed_gain']:>10}x")
        # print(f"{'Graph-First (Hybrid)':<28} | {res_graph_first['summary']['total_exec_time_ms']:>10} ms | {res_graph_first['summary']['speed_gain']:>10}x")
        # print(f"{'SQL-First (Hybrid)':<28} | {res_sql_first['summary']['total_exec_time_ms']:>10} ms | {res_sql_first['summary']['speed_gain']:>10}x")
        # print("=" * 70)

        with open("benchmark_results.json", "w", encoding="utf-8") as f:
            json.dump(complete_output, f, indent=2, ensure_ascii=False)
        print("Đã xuất dữ liệu chi tiết ra file 'benchmark_results.json'!")

    except Exception as e:
        print(f"💥 Lỗi thực thi trong luồng test: {e}")
        
    finally:
        # Đóng kết nối thủ công để giải phóng Connection Pool cho hệ thống
        try:
            sql_db.close()
        except:
            pass
        try:
            neo4j_sess.close()
        except:
            pass

if __name__ == "__main__":
    run_comprehensive_benchmark()