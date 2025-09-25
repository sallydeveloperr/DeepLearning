# data_collector.py
from selenium import webdriver as wd
from selenium.webdriver.chrome.service import Service as sv
from webdriver_manager.chrome import ChromeDriverManager as cdm
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException
import requests
import pandas as pd
import os
import time
from sqlalchemy import text
from dotenv import load_dotenv
from db_manager import get_db_engine, create_tables

load_dotenv()

# ------------------ MOLIT API 데이터 수집 및 정제 ------------------
def fetch_and_process_molit_data():
    """MOLIT API에서 차량 등록 데이터를 수집하고 정규화합니다."""
    print("\n--- MOLIT API 데이터 수집 및 정제 시작 ---")
    api_key = os.getenv("PUBLIC_KEY")
    if not api_key:
        print("환경변수 PUBLIC_KEY가 누락되었습니다. .env 파일을 확인하세요.")
        return pd.DataFrame()
    url = "http://stat.molit.go.kr/portal/openapi/service/rest/getList.do"
    params = {
        "key": api_key,
        "form_id": 5498,
        "style_num": 2,
        "start_dt": 201101,
        "end_dt": 202508
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data["result_data"]["formList"])

        df["reg_date"] = df["date"].astype(str).str[:6]
        value_cols = [c for c in df.columns if any(x in c for x in ["승용", "승합", "화물", "특수"])]
        long_df = df.melt(
            id_vars=["reg_date", "시도명", "시군구"],
            value_vars=value_cols,
            var_name="category",
            value_name="count"
        )
        long_df[["car_type", "usage_type"]] = long_df["category"].str.split(">", expand=True)
        final_df = long_df.rename(columns={"시도명": "sido", "시군구": "sigungu"})
        final_df = final_df[["reg_date", "sido", "sigungu", "car_type", "usage_type", "count"]]

        # None 처리 후 숫자 변환
        final_df["count"] = final_df["count"].replace('None', '0', regex=False)
        final_df["count"] = pd.to_numeric(final_df["count"], errors='coerce').fillna(0).astype(int)

        final_df = final_df[(final_df["usage_type"] != "계") & (final_df["sigungu"] != "계")].copy()

        print("MOLIT API 데이터 정제 완료. 최종 데이터 수:", len(final_df))
        return final_df
    except requests.exceptions.RequestException as e:
        print(f"MOLIT API 호출 오류: {e}")
        return pd.DataFrame()

# ------------------ 현대차 FAQ 크롤링 ------------------
def crawl_hyundai_faq():
    """현대차 웹사이트 FAQ 크롤링"""
    print("--- 현대자동차 FAQ 크롤링 시작 ---")
    url = 'https://www.hyundai.com/kr/ko/faq.html'
    
    options = wd.ChromeOptions()
    options.add_argument('headless')
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    driver = wd.Chrome(service=sv(cdm().install()), options=options)
    wait = WebDriverWait(driver, 10)
    faq_data = []
    
    try:
        print("웹사이트에 접속 중...")
        driver.get(url)
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
                    item_index = faq_items.index(item)
                    
                    cat_text = item.find_element(By.CSS_SELECTOR, "dt i").text.strip()
                    q_text = item.find_element(By.CSS_SELECTOR, "dt .brief").text.strip()

                    if item_index == 0:
                        a_elem = item.find_element(By.CSS_SELECTOR, "dd .exp")
                        a_text = a_elem.text.strip()
                    else:
                        btn = item.find_element(By.CSS_SELECTOR, "dt > button.more")
                        driver.execute_script("arguments[0].click();", btn)
                        wait.until(lambda d: "on" in item.find_element(By.CSS_SELECTOR, "dt").get_attribute("class"))
                        
                        a_elem = item.find_element(By.CSS_SELECTOR, "dd .exp")
                        a_text = a_elem.text.strip()

                        driver.execute_script("arguments[0].click();", btn)
                        wait.until(lambda d: "on" not in item.find_element(By.CSS_SELECTOR, "dt").get_attribute("class"))

                    faq_data.append({
                        "category": cat_text,
                        "question": q_text,
                        "answer": a_text,
                        "source": 0
                    })
                    print(f"  - {q_text[:30]}...")

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
                    wait.until(EC.staleness_of(faq_items[0]))
                    time.sleep(1)
            except Exception:
                print("다음 페이지 버튼 없음 → 종료")
                break

    except Exception as e:
        print(f"크롤링 중 오류 발생: {e}")
        return []
        
    finally:
        driver.quit()
        print(f"\n총 {len(faq_data)}개 FAQ 수집 완료")
    
    return faq_data

# ------------------ 기아차 FAQ 크롤링 (수정) ------------------
def crawl_kia_faq():
    """기아차 웹사이트 FAQ 크롤링"""
    print("--- 기아자동차 FAQ 크롤링 시작 ---")
    url = 'https://www.kia.com/kr/customer-service/center/faq'
    
    options = wd.ChromeOptions()
    options.add_argument('headless')
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    driver = wd.Chrome(service=sv(cdm().install()), options=options)
    wait = WebDriverWait(driver, 10)
    faq_data = []

    try:
        print("웹사이트에 접속 중...")
        driver.get(url)
        driver.maximize_window()
        time.sleep(2)

        try:
            top_btn = WebDriverWait(driver,20).until(EC.element_to_be_clickable((By.CSS_SELECTOR,'#contents > div > div.container.responsivegrid.aem-GridColumn.aem-GridColumn--default--12 > div > div > div.cmp-faq-search-tab > div > div > div > button')))
            top_btn.click()
            all_btn = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.CSS_SELECTOR, '#tab-list > li:nth-child(2) > button')))
            print("'전체' 버튼 클릭 중...")
            driver.execute_script("arguments[0].click();", all_btn)  # JavaScript로 클릭하도록 수정
            time.sleep(2)
        except Exception as e:
            print(f"오류: '전체' 버튼을 찾을 수 없습니다. 계속 진행합니다. {e}")

        page_number = 1
        while True:
            print(f"\n--- {page_number} 페이지 ---")
            
            faq_elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.cmp-accordion__item")))
            num_faq_items = len(faq_elements)
            print(f"FAQ {num_faq_items}개 발견")

            for item_index in range(num_faq_items):
                try:
                    q_text = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, f"#accordion-item-{item_index}-button > span.cmp-accordion__title"))).text.strip()
                    btn = wait.until(EC.presence_of_element_located((By.ID, f"accordion-item-{item_index}-button")))
                    
                    panel_id = f"accordion-item-{item_index}-panel"

                    # 답변 패널이 보이지 않으면 클릭하여 열기
                    if "cmp-accordion__item--expanded" not in btn.get_attribute("class"):
                        driver.execute_script("arguments[0].click();", btn)
                    wait.until(EC.visibility_of_element_located((By.ID, panel_id)))
                    
                    panel_element = driver.find_element(By.ID, panel_id)
                    content_list = []
                    
                    for child in panel_element.find_elements(By.XPATH, ".//*"):
                        if child.tag_name == 'p':
                            content_list.append(child.text.strip())
                        elif child.tag_name == 'img':
                            img_url = child.get_attribute('src')
                            if img_url:
                                content_list.append(f"[이미지: {img_url}]")
                    
                    a_text = "\n".join(content_list)
                    
                    # 다음 항목을 위해 답변 닫기
                    driver.execute_script("arguments[0].click();", btn)
                    wait.until(EC.invisibility_of_element_located((By.ID, panel_id)))

                    faq_data.append({
                        "category": None,
                        "question": q_text,
                        "answer": a_text,
                        "source": 1
                    })
                    print(f"  - {q_text[:30]}...")

                except StaleElementReferenceException:
                    print(f"  ❗ StaleElementReferenceException 발생. FAQ 항목 재탐색 후 재시도.")
                    faq_elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.cmp-accordion__item")))
                    if item_index < len(faq_elements):
                        continue # 현재 항목 재시도
                    else:
                        break # 목록 끝에 도달했으면 중단
                except Exception as e:
                    print(f"  ❗ FAQ 처리 오류: {e}")
                    continue

            # 다음 페이지 버튼 로직
            try:
                current_page_link = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.faq-bottom-paging > div > ul > li.is-active > a')))
                current_page_number = int(current_page_link.text)

                if current_page_number % 5 == 0:
                    next_btn = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.faq-bottom-paging > div > button.pagigation-btn-next')))
                    if 'is-disabled' in next_btn.get_attribute("class"):
                        print("마지막 페이지 도달")
                        break
                    driver.execute_script("arguments[0].click();", next_btn)
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, f'div.faq-bottom-paging > div > ul > li.is-active > a')))
                else:
                    next_page_link_selector = f'div.faq-bottom-paging > div > ul > li:nth-child({(current_page_number % 5) + 1}) > a'
                    try:
                        next_page_link = driver.find_element(By.CSS_SELECTOR, next_page_link_selector)
                        driver.execute_script("arguments[0].click();", next_page_link)
                    except NoSuchElementException:
                        print("더 이상 다음 페이지가 없습니다. 스크래핑 종료.")
                        break

                wait.until(EC.staleness_of(faq_elements[0]))
                page_number += 1
                time.sleep(1)

            except Exception as e:
                print(f"다음 페이지 로직 실행 오류: {e}")
                break

    except Exception as e:
        print(f"크롤링 중 오류 발생: {e}")
        return []
        
    finally:
        driver.quit()
        print(f"\n총 {len(faq_data)}개 FAQ 수집 완료")
    
    return faq_data

# ------------------ 데이터 수집 및 DB 저장 ------------------
def collect_and_save_data():
    """모든 데이터를 수집하고 DB에 저장"""
    engine = get_db_engine()
    create_tables(engine)

    # 1. MOLIT API 데이터 수집 및 저장
    df_molit = fetch_and_process_molit_data()
    if not df_molit.empty:
        df_molit.to_sql("car_regist", con=engine, if_exists="replace", index=False)
        print("✅ MOLIT API 데이터 DB 저장 완료.")

    # 2. 현대차 FAQ 데이터 수집 및 저장
    hyundai_faqs = crawl_hyundai_faq()
    if hyundai_faqs:
        df_hyundai = pd.DataFrame(hyundai_faqs)
        df_hyundai.to_sql('faq', con=engine, if_exists='replace', index=False)
        print("✅ 현대차 FAQ 데이터 DB 저장 완료.")

    # 3. 기아차 FAQ 데이터 수집 및 저장
    kia_faqs = crawl_kia_faq()
    if kia_faqs:
        df_kia = pd.DataFrame(kia_faqs)
        df_kia.to_sql('faq', con=engine, if_exists='append', index=False)
        print("✅ 기아차 FAQ 데이터 DB 추가 저장 완료.")

    engine.dispose()
    print("✅ 모든 데이터 수집 및 DB 저장 작업 완료.")