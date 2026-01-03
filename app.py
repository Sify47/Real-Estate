# app.py - التطبيق الرئيسي
import streamlit as st
import pandas as pd
import requests
import numpy as np
from bs4 import BeautifulSoup
import time
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sqlite3
import json
import os

# إعدادات الصفحة
st.set_page_config(
    page_title="Real Estate Scraper",
    page_icon="🏠",
    layout="wide"
)

# تخصيص التصميم
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        margin: 5px;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# تهيئة قاعدة البيانات
def init_database():
    """تهيئة قاعدة SQLite لتخزين البيانات"""
    conn = sqlite3.connect('real_estate.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS properties (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_type TEXT,
        title TEXT,
        price TEXT,
        location TEXT,
        area TEXT,
        bedrooms TEXT,
        bathrooms TEXT,
        down_payment TEXT,
        payment_method TEXT,
        scraped_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        link TEXT UNIQUE
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS scrape_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scrape_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        properties_count INTEGER,
        status TEXT
    )
    ''')
    
    conn.commit()
    return conn

# دالة لجمع البيانات
def scrape_bayut_page(page_url):
    """دالة لجمع البيانات من صفحة واحدة"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(page_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
    except Exception as e:
        st.error(f"خطأ في تحميل الصفحة: {e}")
        return []
    
    def text_or_none(selector, parent):
        el = parent.select_one(selector)
        return el.get_text(strip=True) if el else None
    
    property_cards = soup.select("ul._172b35d1 li")
    properties = []
    
    for card in property_cards:
        try:
            a = card.select_one("a._8969fafd")
            link = f"https://www.bayut.eg{a.get('href')}" if a and a.get('href') else None
            
            # التحقق من عدم تكرار الرابط
            if link:
                conn = init_database()
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM properties WHERE link = ?", (link,))
                if cursor.fetchone()[0] > 0:
                    continue
            
            price = text_or_none("h4.afdad5da._71366de7 span.eff033a6", card) or text_or_none("span.eff033a6", card)
            title = text_or_none("h2._34c51035", card)
            
            spans = card.select("span._3002c6fb")
            type_ = spans[0].get_text(strip=True) if len(spans) > 0 else None
            bedrooms = spans[1].get_text(strip=True) if len(spans) > 1 else None
            bathrooms = spans[2].get_text(strip=True) if len(spans) > 2 else None
            
            location = text_or_none("h3._51c6b1ca", card)
            d = text_or_none("span.fd7ade6e", card)
            
            area_raw = text_or_none("h4._60820635._07b5f28e", card) or text_or_none("h4", card)
            area = area_raw[:-6] if area_raw and len(area_raw) > 6 else area_raw
            
            properties.append({
                'property_type': type_,
                'link': link,
                'title': title,
                'price': price,
                'location': location,
                'area': area,
                'bedrooms': bedrooms,
                'bathrooms': bathrooms,
                'down_payment': d,
            })
        except Exception as e:
            continue
    
    return properties

# دالة التحديث التلقائي
def auto_scrape_if_needed():
    """التحقق مما إذا كان التحديث مطلوبًا وتنفيذه"""
    conn = init_database()
    cursor = conn.cursor()
    
    # التحقق من آخر تحديث
    cursor.execute("SELECT MAX(scrape_date) FROM scrape_logs WHERE status = 'success'")
    last_scrape = cursor.fetchone()[0]
    
    # إذا مر أكثر من 24 ساعة منذ آخر تحديث
    if last_scrape:
        last_date = datetime.strptime(last_scrape, '%Y-%m-%d %H:%M:%S')
        if datetime.now() - last_date < timedelta(hours=24):
            return False
    
    # تنفيذ التحديث
    try:
        st.info("🔄 جاري التحديث التلقائي للبيانات...")
        
        # جمع البيانات
        base_url = "https://www.bayut.eg/en/alexandria/properties-for-sale/"
        properties = []
        
        for page_num in range(1, 3):  # صفحتين فقط للتحديث اليومي
            if page_num == 1:
                page_url = base_url
            else:
                page_url = f"{base_url.rstrip('/')}/page-{page_num}/"
            
            page_properties = scrape_bayut_page(page_url)
            properties.extend(page_properties)
            time.sleep(1)
        
        # حفظ البيانات في قاعدة البيانات
        for prop in properties:
            try:
                cursor.execute('''
                INSERT OR IGNORE INTO properties 
                (property_type, title, price, location, area, bedrooms, bathrooms, down_payment, link)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    prop['property_type'],
                    prop['title'],
                    prop['price'],
                    prop['location'],
                    prop['area'],
                    prop['bedrooms'],
                    prop['bathrooms'],
                    prop['down_payment'],
                    prop['link']
                ))
            except:
                continue
        
        # تسجيل عملية التحديث
        cursor.execute(
            "INSERT INTO scrape_logs (properties_count, status) VALUES (?, ?)",
            (len(properties), 'success')
        )
        
        conn.commit()
        conn.close()
        st.success(f"✅ تم تحديث {len(properties)} عقار بنجاح")
        return True
        
    except Exception as e:
        st.error(f"❌ خطأ في التحديث التلقائي: {e}")
        cursor.execute(
            "INSERT INTO scrape_logs (properties_count, status) VALUES (?, ?)",
            (0, 'failed')
        )
        conn.commit()
        conn.close()
        return False

# الواجهة الرئيسية
def main():
    st.markdown('<h1 class="main-header">🏠 عقارات الإسكندرية - تحديث تلقائي يومي</h1>', unsafe_allow_html=True)
    
    # الشريط الجانبي
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/3067/3067256.png", width=80)
        st.title("⚙️ التحكم")
        
        if st.button("🔄 تحديث البيانات الآن", type="primary"):
            with st.spinner("جاري جمع البيانات..."):
                auto_scrape_if_needed()
                st.rerun()
        
        st.markdown("---")
        st.markdown("### 📊 الإحصائيات")
        
        conn = init_database()
        cursor = conn.cursor()
        
        # عرض الإحصائيات
        cursor.execute("SELECT COUNT(*) FROM properties")
        total_props = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT location) FROM properties")
        unique_locations = cursor.fetchone()[0]
        
        cursor.execute("SELECT MAX(scrape_date) FROM scrape_logs WHERE status = 'success'")
        last_update = cursor.fetchone()[0]
        
        st.metric("إجمالي العقارات", total_props)
        st.metric("المناطق المختلفة", unique_locations)
        st.metric("آخر تحديث", last_update if last_update else "غير متاح")
        
        conn.close()
    
    # التحقق من التحديث التلقائي عند تحميل الصفحة
    if 'auto_scraped' not in st.session_state:
        auto_scrape_if_needed()
        st.session_state.auto_scraped = True
    
    # المنطقة الرئيسية
    tab1, tab2, tab3 = st.tabs(["🏠 عرض العقارات", "📈 التحليلات", "⚙️ الإعدادات"])
    
    with tab1:
        conn = init_database()
        
        # خيارات التصفية
        col1, col2, col3 = st.columns(3)
        
        with col1:
            locations_query = "SELECT DISTINCT location FROM properties WHERE location IS NOT NULL"
            locations = [row[0] for row in conn.execute(locations_query).fetchall()]
            selected_location = st.selectbox("المنطقة", ["الكل"] + locations)
        
        with col2:
            types_query = "SELECT DISTINCT property_type FROM properties WHERE property_type IS NOT NULL"
            types = [row[0] for row in conn.execute(types_query).fetchall()]
            selected_type = st.selectbox("نوع العقار", ["الكل"] + types)
        
        with col3:
            sort_by = st.selectbox("ترتيب حسب", ["الأحدث", "السعر", "المنطقة"])
        
        # بناء الاستعلام
        query = "SELECT * FROM properties WHERE 1=1"
        params = []
        
        if selected_location != "الكل":
            query += " AND location = ?"
            params.append(selected_location)
        
        if selected_type != "الكل":
            query += " AND property_type = ?"
            params.append(selected_type)
        
        if sort_by == "الأحدث":
            query += " ORDER BY scraped_date DESC"
        elif sort_by == "السعر":
            query += " ORDER BY price DESC"
        elif sort_by == "المنطقة":
            query += " ORDER BY location"
        
        # جلب البيانات
        df = pd.read_sql_query(query, conn, params=params)
        
        if not df.empty:
            st.dataframe(
                df[['title', 'price', 'location', 'property_type', 'bedrooms', 'bathrooms', 'area', 'scraped_date']],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.warning("⚠️ لا توجد عقارات تطابق معايير البحث")
        
        conn.close()
    
    with tab2:
        st.markdown("### 📈 التحليلات الإحصائية")
        
        conn = init_database()
        
        # رسومات بيانية
        col1, col2 = st.columns(2)
        
        with col1:
            # توزيع العقارات حسب المنطقة
            location_counts = pd.read_sql_query(
                "SELECT location, COUNT(*) as count FROM properties GROUP BY location ORDER BY count DESC LIMIT 10",
                conn
            )
            
            if not location_counts.empty:
                fig1 = px.bar(
                    location_counts,
                    x='location',
                    y='count',
                    title="أفضل 10 مناطق بعدد العقارات"
                )
                st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # توزيع العقارات حسب النوع
            type_counts = pd.read_sql_query(
                "SELECT property_type, COUNT(*) as count FROM properties GROUP BY property_type",
                conn
            )
            
            if not type_counts.empty:
                fig2 = px.pie(
                    type_counts,
                    names='property_type',
                    values='count',
                    title="توزيع العقارات حسب النوع"
                )
                st.plotly_chart(fig2, use_container_width=True)
        
        conn.close()
    
    with tab3:
        st.markdown("### ⚙️ إعدادات التحديث التلقائي")
        
        st.info("""
        **معلومات التحديث التلقائي:**
        - يتم تحديث البيانات تلقائيًا كل 24 ساعة
        - يمكنك التحديث يدويًا باستخدام الزر في الشريط الجانبي
        - يتم تخزين البيانات في قاعدة بيانات SQLite
        - سجل التحديثات محفوظ لمتابعة العمليات
        """)
        
        # عرض سجل التحديثات
        conn = init_database()
        logs = pd.read_sql_query(
            "SELECT * FROM scrape_logs ORDER BY scrape_date DESC LIMIT 10",
            conn
        )
        
        st.markdown("#### 📋 سجل آخر 10 تحديثات")
        st.dataframe(logs, use_container_width=True)
        
        # خيارات متقدمة
        with st.expander("خيارات متقدمة"):
            if st.button("🗑️ مسح قاعدة البيانات"):
                conn.execute("DELETE FROM properties")
                conn.execute("DELETE FROM scrape_logs")
                conn.commit()
                st.success("تم مسح قاعدة البيانات")
                st.rerun()
        
        conn.close()

if __name__ == "__main__":
    main()
