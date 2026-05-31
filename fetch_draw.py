# fetch_draw.py - 修正版抓取腳本
import requests
from playwright.sync_api import sync_playwright
import sys
import re

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
            
            # 方法1：從頁面中提取所有開獎資料
            result = page.evaluate('''
                () => {
                    const items = document.querySelectorAll('.result-item');
                    if (items.length === 0) return null;
                    
                    // 取第一筆（最新一期）
                    const firstItem = items[0];
                    
                    // 找日期
                    const dateElem = firstItem.querySelector('.period-date');
                    if (!dateElem) return null;
                    const dateText = dateElem.innerText;
                    const dateMatch = dateText.match(/(\\d{3})\\/(\\d{1,2})\\/(\\d{1,2})/);
                    if (!dateMatch) return null;
                    
                    const year = parseInt(dateMatch[1]) + 1911;
                    const month = dateMatch[2].padStart(2, '0');
                    const day = dateMatch[3].padStart(2, '0');
                    
                    // 找大小順序的號碼
                    let numbers = [];
                    const ballContainer = firstItem.querySelector('.result-item-simple-area-ball-container');
                    if (ballContainer) {
                        const balls = ballContainer.querySelectorAll('.ball');
                        for (const ball of balls) {
                            const num = parseInt(ball.innerText);
                            if (!isNaN(num) && num >= 1 && num <= 39) {
                                numbers.push(num);
                            }
                        }
                    }
                    
                    // 如果上面的方法沒找到，嘗試其他選擇器
                    if (numbers.length !== 5) {
                        const allBalls = firstItem.querySelectorAll('.ball');
                        for (const ball of allBalls) {
                            const num = parseInt(ball.innerText);
                            if (!isNaN(num) && num >= 1 && num <= 39 && !numbers.includes(num)) {
                                numbers.push(num);
                            }
                            if (numbers.length === 5) break;
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
            
            if result and result.numbers and len(result.numbers) == 5:
                print(f"✅ 抓取成功: {result['date']} -> {result['numbers']}")
                return result
            else:
                print("❌ 解析號碼失敗")
                return None
                
        except Exception as e:
            print(f"❌ 抓取失敗: {e}")
            browser.close()
            return None

def send_to_cloud_run(date, numbers):
    """將抓到的號碼發送到 Cloud Run"""
    url = f"{CLOUD_RUN_URL}/api/admin/update_draw"
    payload = {"date": date, "numbers": numbers}
    
    try:
        resp = requests.post(url, json=payload, timeout=30)
        if resp.status_code == 200 and resp.json().get('success'):
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
    
    if draw:
        send_to_cloud_run(draw['date'], draw['numbers'])
    else:
        print("抓取失敗")
        sys.exit(1)
