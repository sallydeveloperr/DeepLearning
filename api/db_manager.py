from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

def get_db_engine():
    """MySQL 데이터베이스 연결 엔진 생성"""
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST")
    db_name = os.getenv("DB_NAME")
    missing_vars = [v for v in ["DB_USER", "DB_PASSWORD", "DB_HOST", "DB_NAME"] if not os.getenv(v)]
    if missing_vars:
        raise ValueError(f"환경변수 누락: {', '.join(missing_vars)}. .env 파일을 확인하세요.")
    db_url = f"mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}"
    return create_engine(db_url, pool_pre_ping=True)

def create_tables(engine):
    """필요한 테이블(car_regist, faq) 생성"""
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS car_regist (
                reg_date VARCHAR(6) NOT NULL,
                sido VARCHAR(50) NOT NULL,
                sigungu VARCHAR(50) NOT NULL,
                car_type VARCHAR(50) NOT NULL,
                usage_type VARCHAR(50) NOT NULL,
                count INT NOT NULL,
                PRIMARY KEY (reg_date, sido, sigungu, car_type, usage_type)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS faq (
                id INT AUTO_INCREMENT PRIMARY KEY,
                category VARCHAR(50),
                question TEXT,
                answer TEXT,
                source INT
            )
        """))
        conn.commit()
    print("✅ 데이터베이스 테이블 생성 완료.")