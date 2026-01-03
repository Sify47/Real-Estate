import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime

def scrape_bayut_simple():
    """دالة مبسطة لجمع البيانات من Bayut"""
    
    print("🔍 Starting data collection from Bayut...")
    
    properties = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    # جمع من 3 صفحات فقط للسرعة
    for page in range(1, 4):
        try:
            if page == 1:
                url = "https://www.bayut.eg/en/alexandria/properties-for-sale/"
            else:
                url = f"https://www.bayut.eg/en/alexandria/properties-for-sale/page-{page}/"
            
            print(f"📄 Collecting page {page}...")
            
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # البحث عن العقارات
            cards = soup.find_all('li', {'data-testid': 'listing-card'})
            
            for card in cards:
                try:
                    # استخراج البيانات الأساسية
                    title_elem = card.find('h2')
                    title = title_elem.text.strip() if title_elem else "N/A"
                    
                    price_elem = card.find('span', class_='ef033a6')
                    price = price_elem.text.strip() if price_elem else "N/A"
                    
                    location_elem = card.find('h3')
                    location = location_elem.text.strip() if location_elem else "N/A"
                    
                    # تنظيف السعر
                    if price != "N/A":
                        price = price.replace('EGP', '').replace(',', '').strip()
                        try:
                            price = float(price)
                        except:
                            price = 0
                    
                    # إضافة للقائمة
                    properties.append({
                        'Title': title,
                        'Price': price if price != "N/A" else 0,
                        'Location': location,
                        'State': 'Alexandria',  # افتراضياً
                        'PropertyType': 'Apartment',  # افتراضياً
                        'Bedrooms': 2,  # افتراضياً
                        'Bathrooms': 1,  # افتراضياً
                        'Area': 100,  # افتراضياً
                        'Payment_Method': 'Cash',  # افتراضياً
                        'Scraped_Date': datetime.now().strftime('%Y-%m-%d'),
                        'Source': 'Bayut'
                    })
                    
                except Exception as e:
                    continue
            
            time.sleep(1)  # تأخير بين الصفحات
            
        except Exception as e:
            print(f"❌ Error on page {page}: {e}")
            continue
    
    print(f"✅ Collected {len(properties)} properties")
    return pd.DataFrame(properties)

def run_scraping():
    """الدالة الرئيسية للـ Scraping"""
    
    print("🚀 Starting scraping process...")
    
    # جمع البيانات من Bayut
    df_bayut = scrape_bayut_simple()
    
    # تنظيف البيانات الأساسية
    df_clean = clean_data(df_bayut)
    
    print(f"🎯 Final data: {len(df_clean)} properties")
    
    return df_clean

def clean_data(df):
    """تنظيف البيانات الأساسية"""
    
    if df.empty:
        return df
    
    # نسخة من البيانات
    df_clean = df.copy()
    
    # إزالة الصفوف الفارغة في الأعمدة المهمة
    df_clean = df_clean.dropna(subset=['Title', 'Price', 'Location'])
    
    # إزالة التكرارات
    df_clean = df_clean.drop_duplicates(subset=['Title', 'Location'])
    
    # تحويل الأنواع
    df_clean['Price'] = pd.to_numeric(df_clean['Price'], errors='coerce')
    df_clean['Area'] = pd.to_numeric(df_clean['Area'], errors='coerce')
    df_clean['Bedrooms'] = pd.to_numeric(df_clean['Bedrooms'], errors='coerce')
    df_clean['Bathrooms'] = pd.to_numeric(df_clean['Bathrooms'], errors='coerce')
    
    # تعبئة القيم الفارغة
    df_clean = df_clean.fillna({
        'PropertyType': 'Unknown',
        'Bedrooms': 0,
        'Bathrooms': 0,
        'Area': 0,
        'Payment_Method': 'Unknown'
    })
    
    return df_clean

if __name__ == "__main__":
    # للتجربة المحلية
    df = run_scraping()
    print(df.head())
