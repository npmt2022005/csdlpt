from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from backend.app.service.graph_first_service import execute_graph_first
from backend.app.service.sql_first_service import execute_sql_first
from sqlalchemy.orm import Session
from backend.app.config.database import get_sql_db
from backend.app.config.neo4j_config import get_neo4j_session
import tracemalloc
import time

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Cho phép tất cả các nguồn truy cập
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/query/bacon")
def run_cross_model_query(
    actor: str = "Kevin Bacon", 
    depth: int = 2, 
    min_revenue: int = 100000000, 
    limit: int = 25, 
    strategy: str = "gf", 
    dataset_size: str = "large",
    db: Session = Depends(get_sql_db),
    neo4j_session = Depends(get_neo4j_session)
):
    gf_data = execute_graph_first(
        sql_db=db, 
        neo4j_session=neo4j_session,
        actor_name=actor, 
        depth=depth, 
        min_revenue=min_revenue,
        dataset_size=dataset_size
    )
    sf_data = execute_sql_first(
        sql_db=db, 
        neo4j_session=neo4j_session,
        actor_name=actor, 
        depth=depth, 
        min_revenue=min_revenue,
        dataset_size=dataset_size
    )
    

    if strategy == "gf":
        final_results = gf_data["results"]
        actors_found = gf_data["actors_found"]  
    else:
        final_results = sf_data["results"]
        actors_found = sf_data["actors_found"]
    
    final_results = final_results[:limit]

    return {
        "results": final_results,
        "actors_found": actors_found,
        "benchmark": {
            "gf": gf_data["benchmark"]["gf"], 
            "sf": sf_data["benchmark"]["sf"]
        }
    }
@app.get("/benchmark/bacon")
def run_benchmark_api(
    actor: str = "Kevin Bacon",
    depth: int = 2,
    min_revenue: float = 100000000.0,
    runs: int = 10,
    sql_db=Depends(get_sql_db),   
    dataset_size: str = "large",
    neo4j_session=Depends(get_neo4j_session) #
):
    print(f"🚀 Bắt đầu Benchmark: {runs} runs, Depth {depth}, Dataset: {actor}")
    benchmark_results = []
    for i in range(runs):
        tracemalloc.start()
        start_cpu_gf = time.process_time()
        start_wall_gf = time.perf_counter()
        gf_data = execute_graph_first(sql_db, neo4j_session, actor, depth, min_revenue,dataset_size)
        wall_gf = (time.perf_counter() - start_wall_gf) * 1000
        cpu_gf = (time.process_time() - start_cpu_gf) * 1000
        mem_gf = tracemalloc.get_traced_memory()[1] / (1024 * 1024) 
        tracemalloc.stop()

        # ---------------------------------------------------------
        # 2. ĐO LƯỜNG SQL-FIRST
        # ---------------------------------------------------------
        tracemalloc.start()
        start_cpu_sf = time.process_time()
        start_wall_sf = time.perf_counter()
        sf_data = execute_sql_first(sql_db, neo4j_session, actor, depth, min_revenue,dataset_size)

        wall_sf = (time.perf_counter() - start_wall_sf) * 1000
        cpu_sf = (time.process_time() - start_cpu_sf) * 1000
        mem_sf = tracemalloc.get_traced_memory()[1] / (1024 * 1024)
        tracemalloc.stop()
        gf_bench = gf_data.get("benchmark", {}).get("gf", {})
        sf_bench = sf_data.get("benchmark", {}).get("sf", {})
        benchmark_results.append({
            "run_id": i + 1,
            "gf": {
                "t1": gf_bench.get("t1"),
                "t2": gf_bench.get("t2"),
                "t3": gf_bench.get("t3"),
                "t_total": round(wall_gf, 2),
                "cpu": round(cpu_gf, 2),
                "inter_size": gf_bench.get("inter_size"),
                "rows_scanned": gf_bench.get("rows_scanned"),
                "mem_mb": round(mem_gf, 2),
                "result_count": len(gf_data.get('results', []))
            },
            "sf": {
                "t1": sf_bench.get("t1"),
                "t2": sf_bench.get("t2"),
                "t3": sf_bench.get("t3"),
                "t_total": round(wall_sf, 2),
                "cpu": round(cpu_sf, 2),
                "inter_size": sf_bench.get("inter_size"),
                "rows_scanned": sf_bench.get("rows_scanned"),
                "mem_mb": round(mem_sf, 2),
                "result_count": len(sf_data.get('results', []))
            }
        })
        
        # In log để theo dõi tiến độ trên Terminal
        print(f"  -> Run {i+1}/{runs} done. GF: {round(wall_gf,1)}ms | SF: {round(wall_sf,1)}ms")

    return {"runs": benchmark_results}



# uvicorn backend.app.main:app --reload --port 8000


