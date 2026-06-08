import pandas as pd
import psycopg2
from neo4j import GraphDatabase
from psycopg2.extras import execute_batch
import json

# Cấu hình
PG_CONFIG = {
    "dbname":"movie_data",
    "user": "postgres",
    "password": "Thuc2022005@",
    "host": "localhost",
}
NEO4J_CONFIG = {
    "uri" : "bolt://localhost:7687",
    "user" : "neo4j",
    "password": "Thuc2022005"
}

movies_df = pd.read_csv("tmdb_5000_movies.csv")
print(movies_df.info())
credits_df = pd.read_csv("tmdb_5000_credits.csv")
print(credits_df.info())

df = pd.merge(movies_df, credits_df, left_on='id', right_on='movie_id')
print(df.info())
def ingest_postgres():
    conn = psycopg2.connect(**PG_CONFIG)
    curr = conn.cursor()

    print("Đang nạp dữ liệu vào Postgres...")

    # Bộ nhớ đệm để thực hiện bulk insert (tăng tốc độ nạp dữ liệu)
    movies_data = []
    actors_data = {}  
    cast_data = []

    for _, row in df.iterrows():
        movie_id = str(row['id'])
        
        # 1. Thu thập dữ liệu Phim
        movies_data.append((movie_id, row['title_x'], row['revenue'], row['budget']))
        
        # 2. Xử lý chuỗi JSON của cột 'cast'
        # Thêm try-except đề phòng trường hợp dòng dữ liệu bị lỗi format hoặc trống
        try:
            cast_list = json.loads(row['cast']) if isinstance(row['cast'], str) else []
            for member in cast_list:
                actor_id = member.get('id')
                actor_name = member.get('name')
                
                if actor_id:
                    # Lưu vào danh sách Actors (Key-Unique để không trùng trong 1 batch)
                    actors_data[actor_id] = (actor_id, actor_name)
                    # Lưu vào danh sách bảng quan hệ Movie_Cast
                    cast_data.append((movie_id, actor_id))
        except (json.JSONDecodeError, TypeError) as e:
            print(f"Lỗi parse JSON cast ở phim ID {movie_id}: {e}")
            continue

    # --- Thực hiện Insert hàng loạt (Bulk Insert) để tối ưu hiệu năng ---
    
    # Insert vào bảng Phim
    print("-> Đang nạp bảng Box_Office_Revenue...")
    execute_batch(curr, """
        INSERT INTO Box_Office_Revenue (movie_id, title, revenue, budget)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (movie_id) DO NOTHING
    """, movies_data)

    # Insert vào bảng Diễn viên
    print("-> Đang nạp bảng Actors...")
    execute_batch(curr, """
        INSERT INTO Actors (actor_id, name, gender)
        VALUES (%s, %s, %s)
        ON CONFLICT (actor_id) DO NOTHING
    """, list(actors_data.values()))

    # Insert vào bảng trung gian Cast
    print("-> Đang nạp bảng Movie_Cast...")
    execute_batch(curr, """
        INSERT INTO Movie_Cast (movie_id, actor_id, character_name, cast_id)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (movie_id, actor_id) DO NOTHING
    """, cast_data)

    conn.commit()
    curr.close()
    conn.close()
    print("Xong Postgres hoàn toàn!")

# BƯỚC 2: NẠP VÀO NEO4J (GRAPH)

def ingest_neo4j():
    # 1. Kết nối với Neo4j
    driver = GraphDatabase.driver(
        NEO4J_CONFIG["uri"], 
        auth=(NEO4J_CONFIG["user"], NEO4J_CONFIG["password"])
    )

    # 2. Chuẩn bị dữ liệu (Flattening)
    movies = []
    casts = []

    for _, row in df.iterrows():
        movies.append({
            "id": str(row['id']),
            "title": row.get('title_x', 'Unknown'),
            "revenue": float(row.get('revenue', 0)),
            "budget": float(row.get('budget', 0))
        })
        
        # Xử lý diễn viên
        try:
            cast_list = json.loads(row['cast'])
            for actor in cast_list:
                casts.append({
                    "movie_id": str(row['id']),
                    "actor_id": str(actor.get('id', actor['name'])),
                    "name": actor['name']
                })
        except: continue
    print("--- KẾT QUẢ KIỂM TRA BIẾN ---")
    print(f"Tổng số phim thu thập được: {len(movies)}")
    print(f"Tổng số diễn viên thu thập được: {len(casts)}")
    
    # In thử 2 phần tử đầu tiên của danh sách movies (nếu có)
    print("\nVí dụ dữ liệu 2 bộ phim đầu tiên:")
    if len(movies) > 0:
        for m in movies[:2]:
            print(m)
    else:
        print("Mảng movies đang rỗng!")

    # In thử 2 phần tử đầu tiên của danh sách casts (nếu có)
    print("\nVí dụ dữ liệu 2 diễn viên đầu tiên:")
    if len(casts) > 0:
        for c in casts[:2]:
            print(c)
    else:
        print("Mảng casts đang rỗng!")
    print("-----------------------------\n")
    # ── HÀM PHỤ: Chia nhỏ mảng dữ liệu khổng lồ thành các cụm nhỏ (Mỗi cụm 1000 dòng) ──
    # def batch_list(iterable, n=1000):
    #     length = len(iterable)
    #     for ndx in range(0, length, n):
    #         yield iterable[ndx:min(ndx + n, length)]

    # # 3. Nạp dữ liệu an toàn theo cụm (Batching)
    # print(f"Bắt đầu tiến trình nạp dữ liệu: {len(movies)} phim và {len(casts)} mối quan hệ...")
    
    # # ĐÃ SỬA: Thay database="castrelationships" thành "neo4j" để chạy được trên bản Community
    # with driver.session(database="castrelationships") as session:
    #     try:
    #         # A. Nạp dữ liệu Movie theo từng cụm 1000 phần tử
    #         for chunk in batch_list(movies, 1000):
    #             session.run("""
    #                 UNWIND $batch AS row
    #                 MERGE (m:Movie {id: row.id})
    #                 SET m += row
    #             """, batch=chunk)
    #         print("-> [OK] Đã nạp xong danh sách Movie.")

    #         # B. Nạp dữ liệu Actor và mối quan hệ theo từng cụm 1000 phần tử
    #         inserted_count = 0
    #         for chunk in batch_list(casts, 1000):
    #             session.run("""
    #                 UNWIND $batch AS row
    #                 MERGE (a:Actor {id: row.actor_id})
    #                 ON CREATE SET a.name = row.name
    #                 WITH row, a
    #                 MATCH (m:Movie {id: row.movie_id})
    #                 MERGE (a)-[:ACTED_IN]->(m)
    #             """, batch=chunk)
    #             inserted_count += len(chunk)
    #             print(f"   ...Đã nạp thành công {inserted_count}/{len(casts)} quan hệ.")
            
    #         print("-> [SUCCESS] Chúc mừng! Toàn bộ dữ liệu đồ thị đã được nạp thành công 100%!")

    #     except Exception as e:
    #         # Bọc lỗi thật để tránh tình trạng nạp lỗi hệ thống vẫn hiện "Nạp hoàn tất"
    #         print(f"-> [ERROR] Quá trình nạp dữ liệu bị hủy bỏ giữa chừng do lỗi: {e}")

    # driver.close()



# if __name__ == "__main__":
#     ingest_neo4j()


    # python -m backend.app.ingest_data 