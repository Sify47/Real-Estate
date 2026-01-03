import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
import sys

# إضافة مسار مجلد src للمكتبات
sys.path.append('.')

# إعداد صفحة Streamlit
st.set_page_config(
    page_title="Real Estate Dashboard",
    page_icon="🏠",
    layout="wide"
)

# CSS بسيط
st.markdown("""
<style>
    .main-title {
        text-align: center;
        color: #1E3A8A;
        padding: 20px;
    }
    .stButton>button {
        width: 100%;
        background-color: #1E3A8A;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# العنوان الرئيسي
st.markdown('<h1 class="main-title">🏠 Real Estate Dashboard - مصر</h1>', unsafe_allow_html=True)

# تبويبات للتنقل
tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "🔄 Update Data", "ℹ️ About"])

with tab1:
    # عرض البيانات
    st.subheader("📈 Real Estate Analysis")
    
    try:
        # محاولة تحميل البيانات
        df = pd.read_csv("data/properties.csv")
        
        # فلاتر بسيطة في Sidebar
        st.sidebar.header("🔍 Filters")
        
        # فلتر المدينة
        cities = ['All'] + sorted(df['State'].dropna().unique().tolist())
        selected_city = st.sidebar.selectbox("City", cities)
        
        # فلتر نوع العقار
        property_types = ['All'] + sorted(df['PropertyType'].dropna().unique().tolist())
        selected_type = st.sidebar.selectbox("Property Type", property_types)
        
        # فلتر السعر
        min_price, max_price = st.sidebar.slider(
            "Price Range (EGP)",
            int(df['Price'].min()),
            int(df['Price'].max()),
            (int(df['Price'].min()), int(df['Price'].max()))
        )
        
        # تطبيق الفلاتر
        filtered_df = df.copy()
        
        if selected_city != 'All':
            filtered_df = filtered_df[filtered_df['State'] == selected_city]
        
        if selected_type != 'All':
            filtered_df = filtered_df[filtered_df['PropertyType'] == selected_type]
        
        filtered_df = filtered_df[
            (filtered_df['Price'] >= min_price) & 
            (filtered_df['Price'] <= max_price)
        ]
        
        # عرض KPIs
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Properties", len(filtered_df))
        
        with col2:
            avg_price = filtered_df['Price'].mean()
            st.metric("Avg Price", f"{avg_price:,.0f} EGP")
        
        with col3:
            st.metric("Cities", filtered_df['State'].nunique())
        
        with col4:
            installment_count = (filtered_df['Payment_Method'] == 'Installments').sum()
            st.metric("Installments", installment_count)
        
        # قسم Charts
        st.subheader("📊 Charts")
        
        # Chart 1: توزيع العقارات حسب المدينة
        fig1 = px.bar(
            filtered_df['State'].value_counts().reset_index(),
            x='State',
            y='count',
            title='Properties by City',
            labels={'State': 'City', 'count': 'Count'}
        )
        st.plotly_chart(fig1, use_container_width=True)
        
        # Chart 2: العلاقة بين السعر والمساحة
        fig2 = px.scatter(
            filtered_df,
            x='Area',
            y='Price',
            color='PropertyType',
            size='Bedrooms',
            hover_data=['Location'],
            title='Price vs Area'
        )
        st.plotly_chart(fig2, use_container_width=True)
        
        # عرض جدول البيانات
        st.subheader("📋 Property List")
        st.dataframe(
            filtered_df[['Title', 'PropertyType', 'Price', 'Location', 'Bedrooms', 'Area']].head(20),
            use_container_width=True
        )
        
        # زر تحميل البيانات
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Download CSV",
            csv,
            "real_estate_data.csv",
            "text/csv"
        )
        
    except FileNotFoundError:
        st.warning("⚠️ No data found. Please update data first.")
        st.info("Go to 'Update Data' tab to collect new data")

with tab2:
    st.subheader("🔄 Update Data")
    
    st.write("Click the button below to collect new real estate data:")
    
    if st.button("🚀 Run Scraping Now"):
        with st.spinner("Collecting data from websites..."):
            try:
                # استيراد وتشغيل الـ Scraper
                from scraper import run_scraping
                
                # تشغيل الـ Scraping
                df = run_scraping()
                
                # حفظ البيانات
                os.makedirs("data", exist_ok=True)
                df.to_csv("data/properties.csv", index=False)
                
                st.success(f"✅ Successfully collected {len(df)} properties!")
                st.balloons()
                
            except Exception as e:
                st.error(f"❌ Error: {e}")
    
    # معلومات التحديث
    st.subheader("📅 Update Info")
    
    try:
        if os.path.exists("data/properties.csv"):
            file_time = os.path.getmtime("data/properties.csv")
            last_updated = datetime.fromtimestamp(file_time).strftime("%Y-%m-%d %H:%M")
            
            df_info = pd.read_csv("data/properties.csv")
            
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"**Last Updated:** {last_updated}")
            with col2:
                st.info(f"**Total Properties:** {len(df_info):,}")
    except:
        pass

with tab3:
    st.subheader("ℹ️ About This Dashboard")
    
    st.write("""
    ### 🏠 Real Estate Dashboard
    
    This dashboard automatically collects real estate data from Egyptian websites and displays it in an interactive dashboard.
    
    ### ✨ Features:
    - ✅ Automatic daily data collection
    - ✅ Interactive filters and charts
    - ✅ Price analysis and comparisons
    - ✅ Download data as CSV
    
    ### 🛠️ Tech Stack:
    - Python
    - Streamlit
    - BeautifulSoup (Web Scraping)
    - Plotly (Charts)
    - Pandas (Data Analysis)
    
    ### 📊 Data Sources:
    - Bayut Egypt
    - Property Finder Egypt
    
    ### 🔄 Auto Update:
    Data is automatically updated daily on Streamlit Cloud.
    """)

# Footer
st.markdown("---")
st.markdown("Made with ❤️ using Streamlit | Data updates daily")
