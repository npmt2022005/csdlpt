import time
from sqlalchemy import text 
from sqlalchemy.orm import Session
from neo4j import Session as Neo4jSession
import tracemalloc
import time
from backend.app.config.neo4j_config import get_neo4j_session
from backend.app.config.database import get_sql_db

def execute_sql_first(
    sql_db: Session, 
    neo4j_session: Neo4jSession, 
    actor_name: str = "Kevin Bacon", 
    depth: int = 1, 
    min_revenue: float = 100000000.0,
    dataset_size: str = "large" 
) -> dict :
    tracemalloc.start()
    start_total = time.perf_counter()
    start_cpu   = time.process_time() 
    size_condition = ""
    if dataset_size.lower() == "small":
        size_condition = "AND is_small = TRUE"
    elif dataset_size.lower() == "medium":
        size_condition = "AND is_medium = TRUE"
    label_suffix = f":{dataset_size.capitalize()}" if dataset_size else ""
    
    # ── t1: SQL filter ──────────────────────────────────────
    start_sql = time.perf_counter()
    sql_query = """
        SELECT movie_id, title, revenue
        FROM box_office_revenue
        WHERE revenue > :min_revenue
    """
    if size_condition:
        sql_query += f"{size_condition}"

    sql_query += " ORDER BY revenue DESC"
    sql_query = text(sql_query)

    
    sql_candidates = sql_db.execute(sql_query, {"min_revenue": min_revenue}).fetchall()
    sql_filter_ms = (time.perf_counter() - start_sql) * 1000


    sql_info_map = {
        str(row.movie_id): {"title": row.title, "revenue": row.revenue}
        for row in sql_candidates
    }
    candidate_movie_ids = list(sql_info_map.keys())
    inter_size  = len(candidate_movie_ids) 

    if not candidate_movie_ids:
        tracemalloc.stop()
        return {
            "results": [],
            "actors_found": 0,
            "benchmark": {
                "sf": {
                    "t_total": round((time.perf_counter() - start_total) * 1000, 2),
                    "t1": round(sql_filter_ms, 2),
                    "t2": 0, "t3": 0, "cpu": round((time.process_time() - start_cpu) * 1000, 2),
                    "inter_size": 0, "rows_scanned": 0, "mem_mb": 0
                }
            }
        }
    

    graph_input_ids = candidate_movie_ids



    # ── t2: Graph BFS với movie filter ─────────────────────
    start_graph = time.perf_counter()
    max_hop = int(depth *2)
    cypher_query = f"""
        MATCH (a:Actor{label_suffix} {{name: $actor_name}})
                -[:ACTED_IN*1..{max_hop}]-(co_actor:Actor{label_suffix})
        WHERE a <> co_actor
        WITH co_actor, shortestPath((a)-[:ACTED_IN*]-(co_actor)) AS sp
        MATCH (co_actor)-[:ACTED_IN]->(m:Movie{label_suffix})
        WHERE m.id IN $movie_ids
        RETURN DISTINCT
            co_actor.name  AS actor_name,
            m.id            AS movie_id,
            length(sp) / 2  AS bacon_number
    """
    
    graph_res = neo4j_session.run(cypher_query, actor_name=actor_name, movie_ids=graph_input_ids)
    graph_relations = []

    for row in graph_res:
        graph_relations.append({
            "movie_id": str(row["movie_id"]),
            "actor_name": row["actor_name"],
            "bacon_number": int(row["bacon_number"])
        })
    graph_bfs_ms = (time.perf_counter() - start_graph) * 1000

    if not graph_relations:
        tracemalloc.stop()
        return {
            "results": [],
            "actors_found": 0,
            "benchmark": {
                "sf": {
                    "t_total": round((time.perf_counter() - start_total) * 1000, 2),
                    "t1": round(sql_filter_ms, 2),
                    "t2": round(graph_bfs_ms, 2),
                    "t3": 0, "cpu": round((time.process_time() - start_cpu) * 1000, 2),
                    "inter_size": inter_size, "rows_scanned":0, "mem_mb": 0
                }
            }
        }
    
    # ── t3: Intersection / merge ────────────────────────────
    start_inter = time.perf_counter()
    results_list = []
    unique_actors = set()
    unique_movies = set()
    
    for rel in graph_relations:
        m_id = rel["movie_id"]
        if m_id in sql_info_map:
            info = sql_info_map[m_id]
            unique_actors.add(rel["actor_name"])
            unique_movies.add(m_id)
            
            results_list.append({
                "name": rel["actor_name"],   
                "movie": info["title"],       
                "revenue": float(info["revenue"]),  
                "bacon_num": rel["bacon_number"]  ,
                "year"     : "N/A"
            })
    results_list.sort(key=lambda x: x["revenue"], reverse=True)
    intersection_ms = (time.perf_counter() - start_inter) * 1000
    # Tắt bộ đo RAM
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    mem_mb = round(peak_mem / (1024 * 1024), 2)
    # ── tổng kết ────────────────────────────────────────────

    total_ms    = (time.perf_counter() - start_total) * 1000
    cpu_time_ms = (time.process_time()  - start_cpu)  * 1000

    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    mem_mb = round(peak_mem / (1024 * 1024), 2)
    return {
        "results": results_list,
        "actors_found": len(unique_actors),
        "benchmark": {
            "sf": {
                "t_total": round(total_ms, 2),
                "t1": round(sql_filter_ms, 2),
                "t2": round(graph_bfs_ms, 2),
                "t3": round(intersection_ms, 2),
                "cpu": round(cpu_time_ms, 2),
                "inter_size": inter_size, 
                "rows_scanned": inter_size,          
                "mem_mb": mem_mb
            }
        }
    }
def run_test():
    print("🚀 BẮT ĐẦU CHẠY BÀI TEST: SQL-FIRST TRÊN TẬP SMALL...")
    print("-" * 50)
    
    
    
    sql_gen = get_sql_db()
    neo4j_gen = get_neo4j_session()

    sql_db = next(sql_gen)
    neo4j_session = next(neo4j_gen)

    actor = "Kevin Bacon"
    dataset = "small"
    depth = 2
    min_rev = 100000000.0

    print(f"Tham số: Actor='{actor}', Size='{dataset}', Depth={depth}, MinRev={min_rev}\n")

    try:
        # ---------------------------------------------------------
        # 3. CHẠY HÀM THỰC TẾ
        # ---------------------------------------------------------
        result = execute_sql_first(
            sql_db=sql_db,
            neo4j_session=neo4j_session,
            actor_name=actor,
            depth=depth,
            min_revenue=min_rev,
            dataset_size=dataset
        )

        # ---------------------------------------------------------
        # 4. IN KẾT QUẢ ĐẸP MẮT (FORMAT GIỐNG TEST SCRIPT CHUYÊN NGHIỆP)
        # ---------------------------------------------------------
        print("===== SUMMARY =====")
        print(f"Actors found: {result.get('actors_found', 0)}")
        print(f"Total rows  : {len(result.get('results', []))}")
        
        bench = result.get("benchmark", {}).get("sf", {})
        print(f"Execution   : {bench.get('t_total', 0)} ms\n")

        print("===== BENCHMARK =====")
        for key, value in bench.items():
            print(f"{key}: {value}")
            
        print("\n===== SAMPLE RESULTS (Top 3) =====")
        results_list = result.get("results", [])
        for i, r in enumerate(results_list[:3]):
            print(f"{i+1}. {r['name']} - {r['movie']} (Doanh thu: {r['revenue']})")

    except Exception as e:
        print(f"❌ CÓ LỖI XẢY RA: {e}")
    finally:
        print("-" * 50)
        print("Đã đóng các kết nối Database.")
        # sql_db.close()
        # neo4j_session.close()

if __name__ == "__main__":
    run_test()