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
store_lists=[]
#모든 페이지에 대해서 출력
for row in store_rows:
    store_lists.append(
        (
        row.select('td')[0].text.strip(),   #지역
        row.select('td')[1].text.strip(),   #매장명
        row.select('td')[2].text.strip(),   #현황
        row.select('td')[3].text.strip(),  #주소
        row.select('td')[5].text.strip()#전화번호
        )
    )
print(store_lists)