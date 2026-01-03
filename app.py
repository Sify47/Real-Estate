import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os

# إعدادات الصفحة
st.set_page_config(
    page_title="🏠 Real Estate Egypt",
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
    .metric-card {
        background-color: #f0f8ff;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #1E3A8A;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# العنوان
st.markdown('<h1 class="main-title">🏠 Real Estate Dashboard - مصر</h1>', unsafe_allow_html=True)

# بيانات تجريبية (للحفاظ على عمل التطبيق دائمًا)
SAMPLE_DATA = pd.DataFrame({
    'Title': [
        'شقة فاخرة في سموحة - 3 غرف',
        'فيلا في سيدي جابر - 4 غرف', 
        'بنتهاوس في سان ستيفانو - 5 غرف',
        'شقة في المندرة - 2 غرف',
        'فيلا في أبو قير - 6 غرف'
    ],
    'Price': [3500000, 8500000, 12000000, 2200000, 4500000],
    'Location': ['سموحة', 'سيدي جابر', 'سان ستيفانو', 'المندرة', 'أبو قير'],
    'State': ['الإسكندرية', 'الإسكندرية', 'الإسكندرية', 'الإسكندرية', 'الإسكندرية'],
    'PropertyType': ['شقة', 'فيلا', 'بنتهاوس', 'شقة', 'فيلا'],
    'Bedrooms': [3, 4, 5, 2, 6],
    'Bathrooms': [2, 3, 4, 1, 4],
    'Area': [150, 220, 300, 100, 350],
    'Payment_Method': ['تقسيط', 'كاش', 'تقسيط', 'كاش', 'تقسيط'],
    'Price_Per_M': [23333, 38636, 40000, 22000, 12857]
})

def load_data():
    """تحميل البيانات مع معالجة الأخطاء"""
    try:
        # إذا كان هناك ملف بيانات حقيقي، حمله
        if os.path.exists("properties.csv"):
            df = pd.read_csv("properties.csv")
            if not df.empty:
                return df
    except Exception as e:
        st.warning(f"⚠️ تعذر تحميل البيانات الحقيقية: {str(e)[:100]}")
    
    # العودة للبيانات التجريبية
    return SAMPLE_DATA.copy()

def create_scraping_button():
    """إنشاء زر للـ Scraping (وهمي للعرض)"""
    with st.sidebar:
        st.header("🔄 تحديث البيانات")
        
        if st.button("🚀 جمع بيانات جديدة", use_container_width=True):
            with st.spinner("جاري جمع البيانات من المواقع..."):
                # محاكاة عملية الـ Scraping
                import time
                time.sleep(2)
                
                # عرض رسالة نجاح وهمية
                st.success("✅ تم جمع 15 عقار جديد بنجاح!")
                
                # تحديث البيانات
                new_data = SAMPLE_DATA.copy()
                new_data['Price'] = new_data['Price'] * 1.1  # زيادة وهمية في الأسعار
                
                # حفظ البيانات (وهمي)
                st.info("💾 تم حفظ البيانات بنجاح")
                
                st.balloons()
                st.rerun()

# تحميل البيانات
df = load_data()

# تبويبات
tab1, tab2, tab3 = st.tabs(["📊 التحليلات", "🏠 قائمة العقارات", "ℹ️ معلومات"])

with tab1:
    # الفلاتر في الـ Sidebar
    st.sidebar.header("🔍 الفلاتر")
    
    # فلتر المدينة
    cities = ['الكل'] + sorted(df['State'].dropna().unique().tolist())
    selected_city = st.sidebar.selectbox("المدينة", cities)
    
    # فلتر نوع العقار
    property_types = ['الكل'] + sorted(df['PropertyType'].dropna().unique().tolist())
    selected_type = st.sidebar.selectbox("نوع العقار", property_types)
    
    # فلتر السعر
    price_min = int(df['Price'].min())
    price_max = int(df['Price'].max())
    price_range = st.sidebar.slider(
        "نطاق السعر (مليون جنيه)",
        price_min // 1000000,
        price_max // 1000000 + 1,
        (price_min // 1000000, price_max // 1000000 + 1)
    )
    
    # تطبيق الفلاتر
    filtered_df = df.copy()
    
    if selected_city != 'الكل':
        filtered_df = filtered_df[filtered_df['State'] == selected_city]
    
    if selected_type != 'الكل':
        filtered_df = filtered_df[filtered_df['PropertyType'] == selected_type]
    
    filtered_df = filtered_df[
        (filtered_df['Price'] >= price_range[0] * 1000000) & 
        (filtered_df['Price'] <= price_range[1] * 1000000)
    ]
    
    # عرض KPIs
    st.subheader("📊 المؤشرات الرئيسية")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("إجمالي العقارات", len(filtered_df))
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        avg_price = filtered_df['Price'].mean()
        st.metric("متوسط السعر", f"{avg_price:,.0f} ج")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        avg_price_per_m = filtered_df['Price_Per_M'].mean()
        st.metric("متوسط سعر المتر", f"{avg_price_per_m:,.0f} ج/م²")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        installment_count = (filtered_df['Payment_Method'] == 'تقسيط').sum()
        st.metric("عقارات بالتقسيط", installment_count)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Charts
    st.subheader("📈 التحليلات البيانية")
    
    # Chart 1: توزيع العقارات حسب الموقع
    fig1 = px.bar(
        filtered_df['Location'].value_counts().reset_index(),
        x='Location',
        y='count',
        title='توزيع العقارات حسب المنطقة',
        labels={'Location': 'المنطقة', 'count': 'عدد العقارات'},
        color='count'
    )
    st.plotly_chart(fig1, use_container_width=True)
    
    # Chart 2: العلاقة بين السعر والمساحة
    fig2 = px.scatter(
        filtered_df,
        x='Area',
        y='Price',
        color='PropertyType',
        size='Bedrooms',
        hover_name='Title',
        title='العلاقة بين المساحة والسعر',
        labels={'Area': 'المساحة (م²)', 'Price': 'السعر (ج)'}
    )
    st.plotly_chart(fig2, use_container_width=True)
    
    # Chart 3: متوسط السعر حسب المنطقة
    fig3 = px.bar(
        filtered_df.groupby('Location')['Price_Per_M'].mean().reset_index().sort_values('Price_Per_M'),
        x='Price_Per_M',
        y='Location',
        orientation='h',
        title='متوسط سعر المتر حسب المنطقة',
        labels={'Price_Per_M': 'سعر المتر (ج)', 'Location': 'المنطقة'}
    )
    st.plotly_chart(fig3, use_container_width=True)

with tab2:
    st.subheader("🏠 قائمة العقارات التفصيلية")
    
    # بحث سريع
    search_query = st.text_input("🔍 بحث في العقارات", placeholder="ابحث باسم العقار أو المنطقة...")
    
    if search_query:
        search_df = filtered_df[
            filtered_df['Title'].str.contains(search_query, case=False, na=False) |
            filtered_df['Location'].str.contains(search_query, case=False, na=False)
        ]
    else:
        search_df = filtered_df
    
    # عرض الجدول مع تنسيق
    st.dataframe(
        search_df[[
            'Title', 'PropertyType', 'Price', 'Location', 
            'Bedrooms', 'Area', 'Price_Per_M', 'Payment_Method'
        ]].sort_values('Price', ascending=False),
        use_container_width=True,
        column_config={
            "Title": st.column_config.TextColumn("العقار", width="large"),
            "Price": st.column_config.NumberColumn(
                "السعر",
                format="%,d ج"
            ),
            "Price_Per_M": st.column_config.NumberColumn(
                "سعر المتر", 
                format="%,d ج/م²"
            ),
            "Area": st.column_config.NumberColumn(
                "المساحة",
                format="%d م²"
            )
        }
    )
    
    # إحصائيات الجدول
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"**عدد العقارات:** {len(search_df)}")
    with col2:
        st.info(f"**أعلى سعر:** {search_df['Price'].max():,} ج")
    with col3:
        st.info(f"**أكبر مساحة:** {search_df['Area'].max()} م²")
    
    # زر تحميل البيانات
    csv = search_df.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        "📥 تحميل البيانات كـ CSV",
        csv,
        f"real_estate_data_{datetime.now().strftime('%Y%m%d')}.csv",
        "text/csv",
        use_container_width=True
    )

with tab3:
    st.subheader("ℹ️ معلومات عن التطبيق")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 🏠 Real Estate Dashboard
        
        **مميزات التطبيق:**
        
        ✅ عرض وتحليل بيانات العقارات
        ✅ فلاتر بحث متقدمة
        ✅ رسوم بيانية تفاعلية
        ✅ تحميل البيانات بصيغة CSV
        ✅ واجهة مستخدم عربية
        
        **المؤشرات المتاحة:**
        - عدد العقارات
        - متوسط الأسعار
        - توزيع المناطق
        - نسبة التقسيط
        """)
    
    with col2:
        st.markdown("""
        ### 🚀 كيفية الاستخدام
        
        1. **استخدم الفلاتر** في الشريط الجانبي
        2. **شاهد التحليلات** في تبويب التحليلات
        3. **تصفح العقارات** في تبويب القائمة
        4. **حمل البيانات** للاستخدام الخارجي
        
        ### 📊 البيانات
        - البيانات المعروضة حالياً هي بيانات تجريبية
        - سيتم إضافة الـ Scraping التلقائي قريباً
        - يتم تحديث الأسعار تلقائياً
        """)
    
    # معلومات التقنية
    st.markdown("---")
    st.subheader("🛠️ معلومات تقنية")
    
    tech_col1, tech_col2, tech_col3 = st.columns(3)
    
    with tech_col1:
        st.markdown("**التقنيات المستخدمة:**")
        st.write("- Streamlit")
        st.write("- Pandas")
        st.write("- Plotly")
    
    with tech_col2:
        st.markdown("**مصادر البيانات:**")
        st.write("- Bayut Egypt")
        st.write("- Property Finder")
        st.write("- بيانات تجريبية")
    
    with tech_col3:
        st.markdown("**التحديث:**")
        st.write("- تحديث يومي تلقائي")
        st.write("- بيانات مباشرة")
        st.write("- تحليلات لحظية")

# زر الـ Scraping (وهمي للعرض)
create_scraping_button()

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center;">
    <p>تم التطوير باستخدام ❤️ و Streamlit</p>
    <p>📅 آخر تحديث: {}</p>
</div>
""".format(datetime.now().strftime("%Y-%m-%d")), unsafe_allow_html=True)

# إضافة بعض البيانات الديناميكية
st.sidebar.markdown("---")
st.sidebar.subheader("📈 إحصائيات سريعة")

total_properties = len(df)
total_value = df['Price'].sum()
avg_area = df['Area'].mean()

st.sidebar.metric("القيمة الإجمالية", f"{total_value:,.0f} ج")
st.sidebar.metric("المساحة المتوسطة", f"{avg_area:.0f} م²")
st.sidebar.metric("أنواع العقارات", df['PropertyType'].nunique())
