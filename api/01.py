import pandas as pd
import requests
from sqlalchemy import create_engine, MetaData, Table, Column, String, Integer
from dotenv import load_dotenv
import os

# 환경변수 로드
load_dotenv()

# DB 연결 엔진 생성
engine = create_engine(
    f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:3306/{os.getenv('DB_NAME')}?charset=utf8mb4"
)

# MOLIT API 정보
API_KEY = "4c49d1028d634c258ca4c7b99eb4a134"
MOLIT_URL = "http://stat.molit.go.kr/portal/openapi/service/rest/getList.do"

params = {
    "key": API_KEY,
    "form_id": 5498,
    "style_num": 2,
    "start_dt": 201101,
    "end_dt": 202508
}

# API 호출
response = requests.get(MOLIT_URL, params=params)
response.raise_for_status()

data = response.json()
df = pd.DataFrame(data["result_data"]["formList"])

print("원본 컬럼:", df.columns.tolist())

# YYYYMM 추출
df["reg_date"] = df["date"].astype(str).str[:6]

# 정규화할 컬럼만 선택 (승용/승합/화물/특수 관련)
value_cols = [c for c in df.columns if any(x in c for x in ["승용", "승합", "화물", "특수"])]

# melt로 긴 형태 변환
long_df = df.melt(
    id_vars=["reg_date", "시도명", "시군구"],
    value_vars=value_cols,
    var_name="category",
    value_name="count"
)

# category 분리 → car_type / usage_type
long_df[["car_type", "usage_type"]] = long_df["category"].str.split(">", expand=True)

# 컬럼 정리
final_df = long_df.rename(columns={
    "시도명": "sido",
    "시군구": "sigungu"
})[["reg_date", "sido", "sigungu", "car_type", "usage_type", "count"]]

# 숫자 변환
final_df["count"] = pd.to_numeric(final_df["count"], errors="coerce").fillna(0).astype(int)

# ✅ 지역 내 "계" 제외 (usage_type, sigungu 둘 다 "계"인 행 제외)
final_df = final_df[(final_df["usage_type"] != "계") & (final_df["sigungu"] != "계")].copy()

print(final_df.head())

# 테이블 정의 및 없으면 생성
metadata = MetaData()

car_regist_sido = Table(
    'CAR_REGIST_SIDO', metadata,
    Column('reg_date', String(6), nullable=False),
    Column('sido', String(20), nullable=False),
    Column('sigungu', String(50), nullable=False),
    Column('car_type', String(20), nullable=False),
    Column('usage_type', String(20), nullable=False),
    Column('count', Integer, nullable=False),
)

metadata.create_all(engine)

# DB 적재
final_df.to_sql("CAR_REGIST_SIDO", con=engine, if_exists="append", index=False)

print("✅ 데이터 적재 완료:", len(final_df), "rows")

# usage_type 값 분포 확인
print("✅ usage_type 종류:", final_df["usage_type"].unique())

# usage_type별 row 수 확인
print("✅ usage_type별 건수")
print(final_df.groupby("usage_type").size())

# 최종 row 수 확인
print("✅ 최종 row 수:", len(final_df))

# usage_type 값 확인
print("✅ usage_type 종류:", final_df["usage_type"].unique())
print(final_df.groupby("usage_type").size())

# car_type 값 확인
print("\n✅ car_type 종류:", final_df["car_type"].unique())
print(final_df.groupby("car_type").size())

# car_type × usage_type 조합으로 확인
print("\n✅ car_type × usage_type 건수")
print(final_df.groupby(["car_type", "usage_type"]).size())

# 최종 row 수 확인
print("\n✅ 최종 row 수:", len(final_df))
