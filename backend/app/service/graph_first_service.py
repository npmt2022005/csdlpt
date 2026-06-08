from sqlalchemy.orm import Session
from neo4j import Session as Neo4jSession
import time 
from sqlalchemy import text
from backend.app.config.neo4j_config import get_neo4j_session
from backend.app.config.database import get_sql_db

def execute_graph_first(
        sql_db : Session,
        neo4j_session: Neo4jSession,
        actor_name: str, 
        depth: int = 1,
        min_revenue: float = 100000000.0,
        dataset_size: str = "large"  
) -> dict :
    start_time = time.perf_counter()
    start_cpu = time.process_time() 

    label_suffix = f":{dataset_size.capitalize()}" if dataset_size else ""

    # ── t1: Graph BFS ──────────────────────────────────────
    start_graph = time.perf_counter()
    max_hop = int(depth * 2)
    cypher_query = f"""
        MATCH (a:Actor{label_suffix} {{name: $actor_name}})
            -[:ACTED_IN*1..{max_hop}]-(co_actor:Actor{label_suffix})
        WHERE a <> co_actor
        WITH a, co_actor, shortestPath((a)-[:ACTED_IN*]-(co_actor)) as sp
        MATCH (co_actor) -[:ACTED_IN]->(m: Movie{label_suffix})
        RETURN DISTINCT 
            co_actor.name  AS actor_name,
            m.id            AS movie_id,
            length(sp) / 2  AS bacon_number
        ORDER BY movie_id ASC, actor_name ASC
    """
    graph_result = neo4j_session.run(cypher_query, actor_name=actor_name)

    
    movie_hop_map: dict[str, list] = {}
    for row in graph_result:
        m_id = str(row["movie_id"])
        if m_id not in movie_hop_map:
            movie_hop_map[m_id] = []
        movie_hop_map[m_id].append({        
            "actor_name"  : row["actor_name"],
            "bacon_number": int(row["bacon_number"])
        })
    print(f"DEBUG: Depth={depth} | Số phim tìm thấy (Inter Size): {len(movie_hop_map)}")
    graph_bfs_ms = (time.perf_counter() - start_graph) * 1000

    if not movie_hop_map:
        total_ms = (time.perf_counter() - start_time) * 1000
        cpu_time_ms = (time.process_time() - start_cpu) * 1000
        return {
            "results": [],
            "actors_found": 0,
            "benchmark": {
            "gf": {
                "t_total": round(total_ms, 2),
                "t1": round(graph_bfs_ms, 2),
                "t2": 0.0,
                "t3": 0.0,
                "cpu": round(cpu_time_ms, 2),
                "inter_size": 0,
                "rows_scanned": 0,
                "mem_mb": 0.1
            }
        }
            
        }
    #sử dụng in nên movie_ids phải tuple 
    candidate_ids = list(movie_hop_map.keys()) 
    movie_ids_tuple = tuple(candidate_ids)
    
    inter_size   = len(candidate_ids)         # intermediate set size

    
    start_sql = time.perf_counter()
    sql_query = text("""
        SELECT DISTINCT 
                m.movie_id, 
                m.title, 
                m.revenue
        FROM box_office_revenue m
        WHERE m.movie_id IN :movie_ids AND m.revenue > :min_revenue 
    """)
    
    sql_res = sql_db.execute(sql_query, {"movie_ids": movie_ids_tuple, "min_revenue": min_revenue}).fetchall() 
    sql_filter_ms = (time.perf_counter() - start_sql) * 1000



    # ── t3: Intersection ───────────────────────────────────
    start_inter = time.perf_counter()
    results_list = []
    unique_actors = set()
    unique_movies = set()
    for row in sql_res:
        m_id = str(row.movie_id)
        if m_id in movie_hop_map:
            for graph_info in movie_hop_map[m_id]: 
                unique_actors.add(graph_info["actor_name"])
                unique_movies.add(m_id)              
                results_list.append({
                    "name"  : graph_info["actor_name"],
                    "bacon_num": graph_info["bacon_number"],
                    "movie_id"    : row.movie_id,
                    "movie"       : row.title,
                    "revenue"     : float(row.revenue),
                    "year"        : "N/A "
                })

    intersection_ms = (time.perf_counter() - start_inter) * 1000

    # ── tổng kết ────────────────────────────────────────────
    total_ms    = (time.perf_counter() - start_time) * 1000
    cpu_time_ms = (time.process_time()  - start_cpu)  * 1000

    return {
        "results": results_list, 
        "actors_found": len(unique_actors),
        "benchmark": {
            "gf": {
                "t_total": round(total_ms, 2),
                "t1": round(graph_bfs_ms, 2),
                "t2": round(sql_filter_ms, 2), 
                "t3": round(intersection_ms, 2),
                "cpu": round(cpu_time_ms, 2),
                "inter_size": inter_size,
                "rows_scanned": inter_size, 
                "mem_mb": 0.0
            }
        }
        
    }

def run_test():
    sql_gen = get_sql_db()
    neo4j_gen = get_neo4j_session()

    sql_db = next(sql_gen)
    neo4j_session = next(neo4j_gen)

    try:
        print("🚀 Running Graph-First Test...\n")

        start = time.perf_counter()

        result = execute_graph_first(
            sql_db=sql_db,
            neo4j_session=neo4j_session,
            actor_name="Kevin Bacon",
            depth=2,
            min_revenue=100000000,
            dataset_size="small"
        )

        end = time.perf_counter()

        # ===== OUTPUT =====
        print("===== SUMMARY =====")
        print(f"Actors found: {result['actors_found']}")
        print(f"Total rows : {len(result['results'])}")
        print(f"Execution  : {(end - start)*1000:.2f} ms")

        print("\n===== SAMPLE RESULTS =====")
        for r in result["results"][:10]:
            print(
                f"{r['name']} | Bacon: {r['bacon_num']} | "
                f"Movie: {r['movie']} ({r['movie_id']}) | "
                f"${r['revenue']}"
            )

        print("\n===== BENCHMARK =====")
        for k, v in result["benchmark"]["gf"].items():
            print(f"{k}: {v}")

    finally:
        # ===== CLEANUP =====
        print("\n🧹 Closing sessions...")
        sql_gen.close()
        neo4j_gen.close()


if __name__ == "__main__":
    run_test()