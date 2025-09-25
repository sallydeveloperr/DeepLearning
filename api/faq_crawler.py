from selenium import webdriver as wd
from selenium.webdriver.chrome.service import Service as sv
from webdriver_manager.chrome import ChromeDriverManager as cdm
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import pandas as pd

url = 'https://www.hyundai.com/kr/ko/faq.html'
service = sv(cdm().install())
driver = wd.Chrome(service=service)

wait = WebDriverWait(driver, 10)
faq_data = []

try:
    print("웹사이트에 접속 중...")
    driver.get(url)
    driver.maximize_window()
    time.sleep(2)

    page_number = 1
    while True:
        print(f"\n--- {page_number} 페이지 ---")

        # FAQ 항목 로드
        faq_items = wait.until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.ui_accordion > dl"))
        )
        print(f"FAQ {len(faq_items)}개 발견")

        for item in faq_items:
            try:
                # 질문 요소들
                cat_text = item.find_element(By.CSS_SELECTOR, "dt i").text.strip()
                q_text = item.find_element(By.CSS_SELECTOR, "dt .brief").text.strip()
                btn = item.find_element(By.CSS_SELECTOR, "dt > button.more")

                # 클릭해서 답변 열기
                driver.execute_script("arguments[0].click();", btn)
                wait.until(lambda d: "on" in item.find_element(By.CSS_SELECTOR, "dt").get_attribute("class"))

                # 답변 추출
                a_elem = item.find_element(By.CSS_SELECTOR, "dd .exp")
                a_text = a_elem.text.strip()

                faq_data.append((cat_text, q_text, a_text))
                print(f"  - {q_text[:30]}...")

                # 닫기
                driver.execute_script("arguments[0].click();", btn)
                wait.until(lambda d: "on" not in item.find_element(By.CSS_SELECTOR, "dt").get_attribute("class"))

            except Exception as e:
                print(f"  ❗ FAQ 처리 오류: {e}")
                continue

        # 다음 페이지 버튼
        try:
            next_btn = driver.find_element(By.CSS_SELECTOR, "nav.pagination button.navi.next")
            if next_btn.get_attribute("disabled"):
                print("마지막 페이지 도달")
                break
            else:
                driver.execute_script("arguments[0].click();", next_btn)
                page_number += 1
                wait.until(EC.staleness_of(faq_items[0]))  # 새 페이지 로딩 대기
                time.sleep(1)
        except Exception:
            print("다음 페이지 버튼 없음 → 종료")
            break

finally:
    print("\n\n--- 스크래핑 완료 ---")
    print(f"총 {len(faq_data)}개 FAQ 수집")

    if faq_data:
        df = pd.DataFrame(faq_data, columns=["카테고리", "질문", "답변"])
        df.to_csv("hyundai_faq_all.csv", index=False, encoding="utf-8-sig")
        print("CSV 저장 완료: hyundai_faq_all.csv")

    driver.quit()
