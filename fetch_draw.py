# fetch_draw.py - 自動抓取今彩539開獎號碼（修正版）
import requests
from playwright.sync_api import sync_playwright
import sys

# Cloud Run 網址
CLOUD_RUN_URL = "https://lottery-system-357432099525.asia-east1.run.app"

def fetch_today_draw():
    """使用 Playwright 抓取台彩官網最新開獎號碼"""
    print("正在抓取台彩官網...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            page.goto("https://www.taiwanlottery.com/lotto/result/daily_cash", timeout=30000)
            page.wait_for_selector(".result-item", timeout=15000)
            
            result = page.evaluate('''
                () => {
                    const items = document.querySelectorAll('.result-item');
                    if (items.length === 0) return null;
                    const firstItem = items[0];
                    const dateElem = firstItem.querySelector('.period-date');
                    if (!dateElem) return null;
                    const dateText = dateElem.innerText;
                    const dateMatch = dateText.match(/(\\d{3})\\/(\\d{1,2})\\/(\\d{1,2})/);
                    if (!dateMatch) return null;
                    const year = parseInt(dateMatch[1]) + 1911;
                    const month = dateMatch[2].padStart(2, '0');
                    const day = dateMatch[3].padStart(2, '0');
                    const numbers = [];
                    const balls = firstItem.querySelectorAll('.ball');
                    for (const ball of balls) {
                        const num = parseInt(ball.innerText);
                        if (!isNaN(num) && num >= 1 && num <= 39) {
                            numbers.push(num);
                        }
                    }
                    if (numbers.length !== 5) return null;
                    return {
                        date: `${year}-${month}-${day}`,
                        numbers: numbers.sort((a, b) => a - b)
                    };
                }
            ''')
            
            browser.close()
            return result
            
        except Exception as e:
            print(f"抓取失敗: {e}")
            browser.close()
            return None

def send_to_cloud_run(date, numbers):
    """將抓到的號碼發送到 Cloud Run"""
    url = f"{CLOUD_RUN_URL}/api/admin/update_draw"
    payload = {"date": date, "numbers": numbers}
    
    try:
        resp = requests.post(url, json=payload, timeout=30)
        if resp.status_code == 200:
            print(f"✅ 成功更新 {date}: {numbers}")
            return True
        else:
            print(f"❌ 更新失敗: {resp.text}")
            return False
    except Exception as e:
        print(f"❌ 發送失敗: {e}")
        return False

if __name__ == "__main__":
    print("=== 開始抓取今彩539開獎號碼 ===")
    draw = fetch_today_draw()
    
    if draw and draw.get('numbers'):
        print(f"抓取成功: {draw['date']} -> {draw['numbers']}")
        send_to_cloud_run(draw['date'], draw['numbers'])
    else:
        print("抓取失敗，請檢查官網是否更新")
        sys.exit(1)
