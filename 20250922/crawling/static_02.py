import requests
#데이터를 요청할 주소
url = 'https://www.hollys.co.kr/store/korea/korStore2.do?'
#서버에 보낼 데이터(1페이지를 보여달라는 의미로)
from_data = {
    'pageNo' : 1,
    'sido' : '',
    'gugun' : '',
    'store' : ''

}
response = requests.post(url,data=from_data)

#터미널에서 pip install beautifulsoup4 실행
from bs4 import BeautifulSoup
#response에 있는 문자열로 된 데이터를 beautifulsoup 객체로 변환
soup = BeautifulSoup(response.text,'html.parser')

#원하는 정보를 추출
# #contents > div.content > fieldset > fieldset > div.tableType01 > table > tbody > tr
str_table_rows = '#contents > div.content > fieldset > fieldset > div.tableType01 > table > tbody > tr'
soup.select(str_table_rows)     #soup.select('tbody > tr')로 작성해도 됨
#soup.select('tbody > tr') tbody가 한개밖에 없어서 가능한 것, 만약 여러개면 가장 먼저 만나는 body 출력
store_rows = soup.select(str_table_rows)
print(store_rows[0])
print(soup.select('td')[0].text.strip())    #지역
print(soup.select('td')[1].text.strip())    #매장명
print(soup.select('td')[2].text.strip())    #현황
print(soup.select('td')[3].text.strip())    #주소
print(soup.select('td')[5].text.strip())    #전화번호

#모든 페이지에 대해서 출력
print(store_rows[0])
for idx, row in enumerate (store_rows):
    print(idx+1)
    print(row.select('td')[0].text.strip())    #지역
    print(row.select('td')[1].text.strip())    #매장명
    print(row.select('td')[2].text.strip())    #현황
    print(row.select('td')[3].text.strip())    #주소
    print(row.select('td')[5].text.strip())    #전화번호
    print('*' * 100)

#데이터베이스에 접속하는 방법!
#insert 쿼리문을 이용해서 수집한 데이터를 DB에 저장
#DB 접속
    
import pymysql
from dotenv import load_dotenv
import os
# .env 로드
load_dotenv()

# 1. DB 연결
def get_connection():
    return pymysql.connect(
        host = os.getenv('DB_HOST'),
        user = os.getenv('DB_USER'),
        password = os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME')
    )