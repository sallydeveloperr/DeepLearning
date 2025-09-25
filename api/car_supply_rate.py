import pandas as pd
import requests
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

# -------------------------
# 1. 환경변수 로드 & DB 연결
# -------------------------
load_dotenv()
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")

# DB 연결 (스키마 지정 X)
engine = create_engine(
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:3306/?charset=utf8mb4"
)

# -------------------------
# 2. 스키마 초기화
# -------------------------
with engine.connect() as conn:
    conn.execute(text("DROP DATABASE IF EXISTS mobilitydb;"))
    conn.execute(text("CREATE DATABASE mobilitydb CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;"))
    print("✅ mobilitydb 스키마 초기화 완료")

# 새 스키마 연결
engine = create_engine(
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:3306/mobilitydb?charset=utf8mb4"
)

with engine.connect() as conn:
    # 차량 등록 테이블
    conn.execute(text("""
    CREATE TABLE CAR_REGIST_SIDO (
        reg_date   VARCHAR(6),
        sido       VARCHAR(50),
        sigungu    VARCHAR(50),
        car_type   VARCHAR(20),
        usage_type VARCHAR(20),
        count      INT
    );
    """))

    # 보급률 테이블
    conn.execute(text("""
    CREATE TABLE CAR_SUPPLY_RATE (
        period      VARCHAR(6),
        sido        VARCHAR(50),
        sigungu     VARCHAR(50),
        car_type    VARCHAR(20),
        usage_type  VARCHAR(20),
        count       INT,
        population  BIGINT,
        supply_rate FLOAT
    );
    """))
    print("✅ 테이블 생성 완료")

# -------------------------
# 3. 차량 등록 데이터 (2011~)
# -------------------------
print("🚗 차량 등록 데이터 불러오는 중...")

API_KEY = "4c49d1028d634c258ca4c7b99eb4a134"
MOLIT_URL = "http://stat.molit.go.kr/portal/openapi/service/rest/getList.do"

params = {
    "key": API_KEY,
    "form_id": 5498,
    "style_num": 2,
    "start_dt": 201101,
    "end_dt": 202512
}

response = requests.get(MOLIT_URL, params=params)
response.raise_for_status()
data = response.json()

df = pd.DataFrame(data["result_data"]["formList"])
print("원본 컬럼:", df.columns.tolist())

# 날짜 처리
df["reg_date"] = df["date"].astype(str).str[:6]

value_cols = [c for c in df.columns if any(x in c for x in ["승용", "승합", "화물", "특수"])]
long_df = df.melt(
    id_vars=["reg_date", "시도명", "시군구"],
    value_vars=value_cols,
    var_name="category",
    value_name="count"
)
long_df[["car_type", "usage_type"]] = long_df["category"].str.split(">", expand=True)

veh_final = long_df.rename(columns={
    "시도명": "sido",
    "시군구": "sigungu"
})[["reg_date", "sido", "sigungu", "car_type", "usage_type", "count"]]

veh_final["count"] = pd.to_numeric(veh_final["count"], errors="coerce").fillna(0).astype(int)
veh_final = veh_final[
    (veh_final["usage_type"] != "계") &
    (veh_final["sigungu"] != "계") &
    (veh_final["sido"] != "계")
].copy()

print("✅ 차량 데이터:", len(veh_final), "rows")

# -------------------------
# 4. 인구 데이터 (총인구만)
# -------------------------
print("👥 인구 데이터 불러오는 중...")

pop_path = os.path.join(os.path.dirname(__file__), "population_total_filtered.csv")
pop_df = pd.read_csv(pop_path, encoding="utf-8")

pop_df["reg_date"] = pop_df["year"].astype(str) + pop_df["month"].astype(str).zfill(2)

print("✅ 인구 데이터:", len(pop_df), "rows")

# -------------------------
# 5. Merge & 보급률 계산
# -------------------------
merged = pd.merge(
    veh_final,
    pop_df[["reg_date", "sido", "sigungu", "population"]],
    on=["reg_date", "sido", "sigungu"],
    how="inner"
)

merged["supply_rate"] = (merged["count"] / merged["population"]) * 1000
merged["period"] = merged["reg_date"]

print("✅ 보급률 계산 완료:", len(merged), "rows")
print(merged.head())

# -------------------------
# 6. DB 저장
# -------------------------
veh_final.to_sql("CAR_REGIST_SIDO", con=engine, if_exists="append", index=False)
merged[["period","sido","sigungu","car_type","usage_type","count","population","supply_rate"]].to_sql(
    "CAR_SUPPLY_RATE", con=engine, if_exists="append", index=False
)

print("✅ CAR_REGIST_SIDO 테이블 저장 완료")
print("✅ CAR_SUPPLY_RATE 테이블 저장 완료")