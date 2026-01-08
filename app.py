import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import os
import requests
from io import StringIO

# إعدادات الصفحة
st.set_page_config(
    page_title="🏠 Real Estate Egypt",
    page_icon="🏠",
    layout="wide"
)

# CSS مخصص
st.markdown("""
<style>
    .main-title {
        text-align: center;
        color: #1E3A8A;
        padding: 20px;
        font-size: 2.5rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        margin: 10px 0;
    }
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 5px;
        padding: 10px 24px;
        font-weight: bold;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #5a67d8 0%, #6b46c1 100%);
    }
    .update-info {
        background-color: #e8f4fd;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
        border-left: 5px solid #2196F3;
    }
    .github-badge {
        display: inline-block;
        background-color: #24292e;
        color: white;
        padding: 5px 10px;
        border-radius: 5px;
        font-size: 0.8em;
        margin: 2px;
    }
</style>
""", unsafe_allow_html=True)

def load_data():
    """تحميل البيانات من GitHub أو ملف محلي"""
    try:
        # أولاً: محاولة تحميل من GitHub RAW URL
        try:
            # رابط ملف Final1.csv في GitHub (تعديله ليناسب repo الخاص بك)
            github_username = "Sify47"  # غير هذا
            github_repo = "Real-Estate"  # غير هذا
            github_raw_url = f"https://raw.githubusercontent.com/{github_username}/{github_repo}/main/Final1.csv"
            
            response = requests.get(github_raw_url, timeout=10)
            if response.status_code == 200:
                # قراءة البيانات من response
                df = pd.read_csv(StringIO(response.text))
                st.sidebar.success(f"✅ Loaded {len(df)} properties from GitHub")
                
                # محاولة تحميل metadata أيضًا
                try:
                    metadata_url = f"https://raw.githubusercontent.com/{github_username}/{github_repo}/main/scraping_metadata.txt"
                    metadata_response = requests.get(metadata_url, timeout=5)
                    if metadata_response.status_code == 200:
                        metadata = metadata_response.text
                        # استخراج آخر وقت تحديث
                        for line in metadata.split('\n'):
                            if 'Last scraped:' in line:
                                last_update = line.replace('Last scraped:', '').strip()
                                st.session_state['last_update'] = last_update
                                break
                except:
                    pass
                    
                return df
        except Exception as e:
            st.sidebar.warning(f"⚠️ Could not load from GitHub: {str(e)[:100]}")
        
        # ثانياً: محاولة تحميل من ملف محلي (للتنمية المحلية)
        if os.path.exists("Final1.csv") and os.path.getsize("Final1.csv") > 0:
            df = pd.read_csv("Final1.csv")
            if not df.empty:
                st.sidebar.info(f"ℹ️ Loaded {len(df)} properties from local Final1.csv")
                
                # تحميل metadata محلي إذا وجد
                if os.path.exists("scraping_metadata.txt"):
                    try:
                        with open("scraping_metadata.txt", "r") as f:
                            metadata = f.read()
                            for line in metadata.split('\n'):
                                if 'Last scraped:' in line:
                                    st.session_state['last_update'] = line.replace('Last scraped:', '').strip()
                                    break
                    except:
                        pass
                        
                return df
        
        # ثالثاً: بيانات تجريبية
        st.sidebar.info("ℹ️ Using sample data")
        return pd.DataFrame({
            'Title': ['Sample Property 1', 'Sample Property 2'],
            'PropertyType': ['Apartment', 'Villa'],
            'Price': [2000000, 3500000],
            'Location': ['Maadi', 'New Cairo'],
            'State': ['Cairo', 'Cairo'],
            'Bedrooms': [3, 4],
            'Area': [120, 180],
            'Price_Per_M': [16666, 19444],
            'Payment_Method': ['Cash', 'Installments'],
            'Bathrooms': [2, 3],
            'Down_Payment': [0, 500000]
        })
        
    except Exception as e:
        st.sidebar.error(f"❌ Error loading data: {str(e)[:100]}")
        return pd.DataFrame()

# تحميل البيانات
df = load_data()

# إعداد session state لآخر تحديث إذا لم يكن موجود
if 'last_update' not in st.session_state:
    st.session_state['last_update'] = "Unknown"

# العنوان الرئيسي
st.markdown('<h1 class="main-title">🏠 Real Estate Dashboard - مصر</h1>', unsafe_allow_html=True)

# تبويبات
tab1, tab2 = st.tabs(["📊 Dashboard", "ℹ️ About & Updates"])

with tab1:
    # ===== SIDEBAR FILTERS =====
    st.sidebar.header("🔍 Filters")
    
    # فلتر المدينة
    cities = ['All'] + sorted(df['State'].dropna().unique().tolist()) if 'State' in df.columns else ['All']
    selected_city = st.sidebar.selectbox("State", cities)
    
    # فلتر نوع العقار
    property_types = ['All'] + sorted(df['PropertyType'].dropna().unique().tolist()) if 'PropertyType' in df.columns else ['All']
    selected_type = st.sidebar.selectbox("Property Type", property_types)
    
    # فلتر السعر
    if 'Price' in df.columns:
        price_min = int(df['Price'].min())
        price_max = int(df['Price'].max())
        price_range = st.sidebar.slider(
            "Price Range (EGP)",
            price_min,
            price_max,
            (price_min, price_max)
        )
    else:
        price_range = (0, 10000000)
    
    # فلتر المنطقة
    locations = ['All'] + sorted(df['Location'].dropna().unique().tolist()) if 'Location' in df.columns else ['All']
    selected_location = st.sidebar.selectbox("Location", locations)
    
    # فلتر طريقة الدفع
    payment_methods = ['All'] + sorted(df['Payment_Method'].dropna().unique().tolist()) if 'Payment_Method' in df.columns else ['All']
    selected_payment = st.sidebar.selectbox("Payment Method", payment_methods)
    
    # ===== APPLY FILTERS =====
    filtered_df = df.copy()
    
    if selected_city != 'All' and 'State' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['State'] == selected_city]
    
    if selected_type != 'All' and 'PropertyType' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['PropertyType'] == selected_type]
    
    if selected_location != 'All' and 'Location' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Location'] == selected_location]
    
    if selected_payment != 'All' and 'Payment_Method' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Payment_Method'] == selected_payment]
    
    if 'Price' in filtered_df.columns:
        filtered_df = filtered_df[
            (filtered_df['Price'] >= price_range[0]) & 
            (filtered_df['Price'] <= price_range[1])
        ]
    
    # ===== KPIs =====
    st.subheader("📊 Key Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        with st.container():
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Total Properties", len(filtered_df))
            st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        with st.container():
            avg_price = filtered_df['Price'].mean() if 'Price' in filtered_df.columns and not filtered_df.empty else 0
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Avg Price", f"{avg_price:,.0f} EGP" if avg_price > 0 else "N/A")
            st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        with st.container():
            avg_area = filtered_df['Area'].mean() if 'Area' in filtered_df.columns and not filtered_df.empty else 0
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Avg Area", f"{avg_area:.0f} m²" if avg_area > 0 else "N/A")
            st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        with st.container():
            if 'Payment_Method' in filtered_df.columns and not filtered_df.empty:
                installment_count = (filtered_df['Payment_Method'] == 'Installments').sum()
                installment_ratio = (installment_count / len(filtered_df)) * 100 if len(filtered_df) > 0 else 0
            else:
                installment_ratio = 0
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Installments", f"{installment_ratio:.1f}%")
            st.markdown('</div>', unsafe_allow_html=True)
    
    # ===== CHARTS =====
    st.subheader("📈 Analytics")
    fig7 = px.violin(filtered_df, "PropertyType", "Price")
    st.plotly_chart(fig7, use_container_width=True)
    # Chart 1: توزيع العقارات حسب المدينة
    if not filtered_df.empty and 'State' in filtered_df.columns:
        fig1 = px.bar(
            filtered_df['State'].value_counts().reset_index(),
            x='State',
            y='count',
            title='Properties Distribution by City',
            labels={'State': 'City', 'count': 'Number of Properties'},
            color='count',
            color_continuous_scale='Viridis'
        )
        st.plotly_chart(fig1, use_container_width=True)
    
    # Chart 2: العلاقة بين السعر والمساحة
    if len(filtered_df) > 1 and all(col in filtered_df.columns for col in ['Area', 'Price', 'PropertyType', 'Bedrooms']):
        fig2 = px.scatter(
            filtered_df,
            x='Area',
            y='Price',
            color='PropertyType',
            size='Bedrooms',
            hover_name='State' if 'State' in filtered_df.columns else None,
            hover_data=['Location', 'Payment_Method', 'Price_Per_M'] if all(col in filtered_df.columns for col in ['Location', 'Payment_Method', 'Price_Per_M']) else None,
            title='Price vs Area Analysis',
            labels={'Area': 'Area (m²)', 'Price': 'Price (EGP)'}
        )
        st.plotly_chart(fig2, use_container_width=True)
    
    # Chart 3: متوسط سعر المتر حسب المنطقة
    if not filtered_df.empty and 'Location' in filtered_df.columns and 'Price_Per_M' in filtered_df.columns:
        avg_price_by_location = filtered_df.groupby('Location').agg({
            'Price_Per_M': 'mean',
            'Price': 'count'
        }).reset_index()
        
        fig3 = px.bar(
            avg_price_by_location.sort_values('Price_Per_M', ascending=False).head(10),
            x='Location',
            y='Price_Per_M',
            title='Average Price Per m² by Location (Top 10)',
            labels={'Price_Per_M': 'Price per m² (EGP)', 'Location': 'Location'},
            color='Price_Per_M',
            color_continuous_scale='Plasma'
        )
        st.plotly_chart(fig3, use_container_width=True)
    
    # ===== DATA TABLE =====
    st.subheader("📋 Property List")
    
    # بحث في الجدول
    search_query = st.text_input("🔍 Search properties...", placeholder="Type property name or location...")
    
    if search_query and 'Title' in filtered_df.columns and 'Location' in filtered_df.columns:
        display_df = filtered_df[
            filtered_df['Title'].astype(str).str.contains(search_query, case=False, na=False) |
            filtered_df['Location'].astype(str).str.contains(search_query, case=False, na=False)
        ]
    else:
        display_df = filtered_df
    
    # عرض الجدول
    if not display_df.empty:
        # تحديد الأعمدة المتاحة للعرض
        available_columns = []
        for col in ['Title', 'PropertyType', 'Price', 'Location', 'Bedrooms', 'Area', 'Price_Per_M', 'Payment_Method']:
            if col in display_df.columns:
                available_columns.append(col)
        
        st.dataframe(
            display_df[available_columns].head(20),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No properties match your filters. Try adjusting them.")

with tab2:
    st.subheader("ℹ️ About & Auto-Updates")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 🏠 Real Estate Intelligence Platform
        
        **Purpose:**
        This dashboard provides real-time insights into the Egyptian real estate market.
        
        **Key Features:**
        - 📊 Interactive data visualization
        - 🔍 Advanced filtering system
        - 📈 Market trend analysis
        - 💰 Price comparison tools
        
        **Data Source:**
        - Continually updated from Bayut Egypt
        - Historical data preserved
        - Daily new listings added
        
        **For:**
        - Buyers looking for properties
        - Investors analyzing market trends
        - Real estate professionals
        - Market researchers
        """)
    
    with col2:
        st.markdown("""
        ### 🛠️ Technical Architecture
        
        **Built With:**
        - Python 3.9+
        - Streamlit (Frontend)
        - Pandas (Data Processing)
        - Plotly (Visualization)
        - BeautifulSoup (Data Collection)
        
        **Update System:**
        - GitHub Actions for auto-scraping
        - Daily updates at 4:00 AM Egypt Time
        - Incremental data collection
        - Historical data preserved in Final1.csv
        
        **Data Flow:**
        1. Daily scrape → 2. Merge with Final1.csv → 3. Push to GitHub → 4. Streamlit loads
        """)
    
    # معلومات التحديث التلقائي
    st.markdown("---")
    st.subheader("🔄 Automatic Data Updates")
    
    st.markdown("""
    ### 📅 Daily Auto-Scraping System
    
    **How it works:**
    
    1. **Daily Collection** (4:00 AM Egypt Time):
       - GitHub Actions automatically scrapes new properties
       - Cleans and processes the data
       - Merges with existing `Final1.csv`
    
    2. **Data Preservation:**
       - Your existing `Final1.csv` is preserved
       - New properties are **appended** (not overwritten)
       - Duplicates are automatically removed
    
    3. **Automatic Deployment:**
       - Updated `Final1.csv` is pushed to GitHub
       - Streamlit app loads the latest data
       - Dashboard updates automatically
    """)
    
    # عرض معلومات التحديث
    st.markdown("### 📊 Current Data Status")
    
    col_a, col_b, col_c = st.columns(3)
    
    with col_a:
        st.info(f"**Total Properties:** {len(df):,}")
    
    with col_b:
        last_update = st.session_state.get('last_update', 'Unknown')
        st.info(f"**Last Update:** {last_update}")
    
    with col_c:
        # حساب عمر البيانات
        try:
            if last_update != 'Unknown':
                last_dt = datetime.strptime(last_update, '%Y-%m-%d %H:%M:%S')
                age_hours = (datetime.now() - last_dt).total_seconds() / 3600
                
                if age_hours < 24:
                    status = "🟢 Fresh"
                elif age_hours < 48:
                    status = "🟡 Recent"
                else:
                    status = "🔴 Needs Update"
                
                st.info(f"**Data Status:** {status}")
        except:
            st.info("**Data Status:** Checking...")
    
    # معلومات حول Final1.csv
    st.markdown("""
    ### 📁 Data File: Final1.csv
    
    **Features:**
    - Contains **all historical data**
    - **Incremental updates** daily
    - **No data loss** - old properties preserved
    - **Automatic deduplication**
    
    **Next Auto-Scrape:** Daily at 4:00 AM Egypt Time
    """)
    
    # زر لتحديث البيانات يدوياً (اختياري)
    if st.button("🔄 Check for Updates Now", use_container_width=False):
        st.info("Checking for latest data from GitHub...")
        st.rerun()
    
    # معلومات الاستخدام
    st.markdown("---")
    
    expander = st.expander("📖 How to Use This Dashboard")
    with expander:
        st.markdown("""
        1. **Dashboard Tab:**
           - Use filters in sidebar to narrow down properties
           - View key metrics and charts
           - Search properties by name or location
        
        2. **Automatic Updates:**
           - Data updates automatically every morning
           - Historical data is preserved
           - New properties are added daily
        
        3. **Tips:**
           - Check daily for new property listings
           - Use multiple filters for precise searches
           - Monitor price trends with the charts
        """)
    
    # Footer
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align: center; padding: 20px;">
        <p>Developed with ❤️ using Streamlit & GitHub Actions</p>
        <p style="font-size: 0.8em; color: #666;">Version 3.0 | Auto-Updates Enabled | Last app update: {datetime.now().strftime('%Y-%m-%d')}</p>
    </div>
    """, unsafe_allow_html=True)

# معلومات إضافية في الـ Sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("📈 Quick Stats")

if not df.empty:
    if 'Price' in df.columns:
        st.sidebar.metric("Total Value", f"{df['Price'].sum():,.0f} EGP")
    
    if 'Price_Per_M' in df.columns:
        avg_price_m2 = df['Price_Per_M'].mean()
        st.sidebar.metric("Avg Price/m²", f"{avg_price_m2:,.0f} EGP" if avg_price_m2 > 0 else "N/A")
    
    if 'PropertyType' in df.columns:
        st.sidebar.metric("Property Types", df['PropertyType'].nunique())

# معلومات التحديث التلقائي في الـ sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("🔄 Auto-Update Status")

st.sidebar.info(f"""
**Last Update:** {st.session_state.get('last_update', 'Checking...')}

**Next Update:** 4:00 AM Egypt Time

**Data File:** Final1.csv
**Properties:** {len(df):,}
""")

# رابط GitHub Actions (يمكن إضافته إذا أردت)
st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    <div style="text-align: center;">
        <span class="github-badge">GitHub Actions</span>
        <span class="github-badge">Auto-Scraping</span>
        <span class="github-badge">Daily Updates</span>
    </div>
    """,
    unsafe_allow_html=True
)
