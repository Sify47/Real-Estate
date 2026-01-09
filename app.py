import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
import requests
from io import StringIO
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# إعدادات الصفحة
st.set_page_config(page_title="Real Estate Egypt", page_icon="🏠", layout="wide")

# CSS مخصص
st.markdown(
    """
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
    .prediction-card {
        background: linear-gradient(135deg, #4CAF50 0%, #8BC34A 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        margin: 10px 0;
    }
    .recommendation-card {
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        background-color: #f9f9f9;
    }
</style>
""",
    unsafe_allow_html=True,
)


# تحميل البيانات مع cache
@st.cache_data(ttl=300)  # تحديث كل 5 دقائق
def load_data():
    """تحميل البيانات من GitHub أو ملف محلي"""
    try:
        # أولاً: محاولة تحميل من GitHub RAW URL
        try:
            github_username = "Sify47"
            github_repo = "Real-Estate"
            github_raw_url = f"https://raw.githubusercontent.com/{github_username}/{github_repo}/main/Final1.csv"

            response = requests.get(github_raw_url, timeout=10)
            if response.status_code == 200:
                df = pd.read_csv(StringIO(response.text))

                # محاولة تحميل metadata
                try:
                    metadata_url = f"https://raw.githubusercontent.com/{github_username}/{github_repo}/main/scraping_metadata.txt"
                    metadata_response = requests.get(metadata_url, timeout=5)
                    if metadata_response.status_code == 200:
                        metadata = metadata_response.text
                        for line in metadata.split("\n"):
                            if "Last scraped:" in line:
                                st.session_state["last_update"] = line.replace(
                                    "Last scraped:", ""
                                ).strip()
                                break
                except:
                    pass

                return df
        except Exception as e:
            st.sidebar.warning(f"⚠️ Could not load from GitHub: {str(e)[:100]}")

        # ثانياً: محاولة تحميل من ملف محلي
        if os.path.exists("Final1.csv") and os.path.getsize("Final1.csv") > 0:
            df = pd.read_csv("Final1.csv")

            # تحميل metadata محلي
            if os.path.exists("scraping_metadata.txt"):
                try:
                    with open("scraping_metadata.txt", "r") as f:
                        metadata = f.read()
                        for line in metadata.split("\n"):
                            if "Last scraped:" in line:
                                st.session_state["last_update"] = line.replace(
                                    "Last scraped:", ""
                                ).strip()
                                break
                except:
                    pass

            return df

        # ثالثاً: بيانات تجريبية
        return pd.DataFrame(
            {
                "Title": ["Sample Property 1", "Sample Property 2"],
                "PropertyType": ["Apartment", "Villa"],
                "Price": [2000000, 3500000],
                "Location": ["Maadi", "New Cairo"],
                "State": ["Cairo", "Cairo"],
                "Bedrooms": [3, 4],
                "Area": [120, 180],
                "Price_Per_M": [16666, 19444],
                "Payment_Method": ["Cash", "Installments"],
                "Bathrooms": [2, 3],
                "Down_Payment": [0, 500000],
            }
        )

    except Exception as e:
        st.sidebar.error(f"❌ Error loading data: {str(e)[:100]}")
        return pd.DataFrame()


# ========== PRICE PREDICTION FUNCTIONS ==========
def train_price_model(df):
    """تدريب نموذج توقع الأسعار"""
    try:
        features = ["Area", "Bedrooms", "Bathrooms"]
        target = "Price"

        available_features = [f for f in features if f in df.columns]

        if len(available_features) < 2 or target not in df.columns:
            return None

        df_clean = df.dropna(subset=available_features + [target])

        if len(df_clean) < 5:
            return None

        X = df_clean[available_features]
        y = df_clean[target]

        model = LinearRegression()
        model.fit(X, y)

        return model, available_features
    except:
        return None


def predict_property_price(model, features, area, bedrooms, bathrooms):
    """توقع سعر عقار"""
    try:
        input_data = pd.DataFrame(
            [{"Area": area, "Bedrooms": bedrooms, "Bathrooms": bathrooms}]
        )

        predicted_price = model.predict(input_data[features])[0]
        return max(0, float(predicted_price))
    except:
        return None


# ========== RECOMMENDATION FUNCTIONS ==========
def prepare_recommendation_data(df):
    """تحضير بيانات التوصيات"""
    df_copy = df.copy()

    if "Combined_Features" not in df_copy.columns:
        df_copy["Combined_Features"] = ""

        if "PropertyType" in df_copy.columns:
            df_copy["Combined_Features"] += df_copy["PropertyType"].fillna("") + " "

        if "Location" in df_copy.columns:
            df_copy["Combined_Features"] += df_copy["Location"].fillna("") + " "

        if "State" in df_copy.columns:
            df_copy["Combined_Features"] += df_copy["State"].fillna("") + " "

        if "Bedrooms" in df_copy.columns:
            df_copy["Combined_Features"] += df_copy["Bedrooms"].astype(str) + " غرف "

        if "Price" in df_copy.columns:
            price_quantiles = pd.qcut(
                df_copy["Price"], 4, labels=["رخيص", "متوسط", "غالي", "فاخر"]
            )
            df_copy["Combined_Features"] += price_quantiles.astype(str) + " "

    return df_copy


def get_recommendations(df, property_id, n=5):
    """الحصول على توصيات"""
    try:
        df_prepared = prepare_recommendation_data(df)

        tfidf = TfidfVectorizer(stop_words=None)
        tfidf_matrix = tfidf.fit_transform(df_prepared["Combined_Features"])

        cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)

        sim_scores = list(enumerate(cosine_sim[property_id]))
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)[1 : n + 1]

        property_indices = [i[0] for i in sim_scores]

        return df_prepared.iloc[property_indices]
    except:
        return pd.DataFrame()


# ========== MARKET INSIGHTS FUNCTIONS ==========
def calculate_market_insights(df):
    """حساب تحليلات السوق"""
    insights = {}

    if len(df) == 0:
        return insights

    # إحصائيات الأسعار
    if "Price" in df.columns:
        insights["price_stats"] = {
            "mean": df["Price"].mean(),
            "median": df["Price"].median(),
            "min": df["Price"].min(),
            "max": df["Price"].max(),
        }

    # تحليل سعر المتر
    if "Price_Per_M" in df.columns:
        insights["price_per_m_stats"] = {
            "mean": df["Price_Per_M"].mean(),
            "median": df["Price_Per_M"].median(),
        }

    # المناطق الأغلى
    if "Location" in df.columns and "Price_Per_M" in df.columns:
        location_prices = (
            df.groupby("Location")["Price_Per_M"].mean().sort_values(ascending=False)
        )
        insights["expensive_areas"] = location_prices.head(5).to_dict()
        insights["affordable_areas"] = location_prices.tail(5).to_dict()

    # توزيع أنواع العقارات
    if "PropertyType" in df.columns:
        property_dist = df["PropertyType"].value_counts(normalize=True) * 100
        insights["property_distribution"] = property_dist.to_dict()

    # نسبة التقسيط
    if "Payment_Method" in df.columns:
        payment_dist = df["Payment_Method"].value_counts(normalize=True) * 100
        insights["payment_distribution"] = payment_dist.to_dict()

    return insights


# ========== MAIN APPLICATION ==========
# تحميل البيانات
df = load_data()

# إعداد session state
if "last_update" not in st.session_state:
    st.session_state["last_update"] = "Unknown"

# العنوان الرئيسي
st.markdown(
    '<h1 class="main-title">Real Estate Dashboard</h1>',
    unsafe_allow_html=True,
)

# تبويبات
tab1, tab2 = st.tabs(
    [
        "📊 Dashboard",
        # "💰 Price Predictor",
        # "🤖 AI Recommendations",
        "📈 Market Insights",
    ]
)
view = ["Sea" , "Club" , "Street"]
with tab1:  # Dashboard الأساسي
    # ===== SIDEBAR FILTERS =====
    st.sidebar.header("🔍 Filters")

    # فلتر النوع
    property_types = (
        ["All"] + sorted(df["PropertyType"].dropna().unique().tolist())
        if "PropertyType" in df.columns
        else ["All"]
    )
    selected_type = st.sidebar.selectbox("Property Type", property_types)
    # فلتر النوع
    view_types = (
        ["All"] + sorted(view)
        if "Title" in df.columns
        else ["All"]
    )
    selected_view = st.sidebar.selectbox("View", view_types)

    # فلتر المدينة
    cities = (
        ["All"] + sorted(df["State"].dropna().unique().tolist())
        if "State" in df.columns
        else ["All"]
    )
    selected_city = st.sidebar.selectbox("State", cities)

    # فلتر المنطقة
    locations = (
        ["All"] + sorted(df["Location"].dropna().unique().tolist())
        if "Location" in df.columns
        else ["All"]
    )
    selected_location = st.sidebar.selectbox("Location", locations)
    print(df["Price"])
    # فلتر السعر
    if "Price" in df.columns:
        price_min = int(df["Price"].min())
        price_max = int(df["Price"].max())
        price_range = st.sidebar.slider(
            "Price Range (EGP)", price_min, price_max, (price_min, price_max)
        )

    # فلتر المساحة
    if "Area" in df.columns:
        area_min = int(df["Area"].min())
        area_max = int(df["Area"].max())
        area_range = st.sidebar.slider(
            "Area Range (m²)", area_min, area_max, (area_min, area_max)
        )

    # فلتر طريقة الدفع
    payment_methods = (
        ["All"] + sorted(df["Payment_Method"].dropna().unique().tolist())
        if "Payment_Method" in df.columns
        else ["All"]
    )
    selected_payment = st.sidebar.selectbox("Payment Method", payment_methods)

    # ===== تطبيق الفلترات =====
    filtered_df = df.copy()

    if selected_city != "All" and "State" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["State"] == selected_city]

    if selected_type != "All" and "PropertyType" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["PropertyType"] == selected_type]

    if selected_view != "All" and "Title" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["Title"].astype(str).str.contains(selected_view, case=False, na=False)
        ]
        # df[df["Title"].astype(str).str.contains("Sea", case=False, na=False)]

    if selected_location != "All" and "Location" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["Location"] == selected_location]

    if selected_payment != "All" and "Payment_Method" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["Payment_Method"] == selected_payment]

    if "Price" in filtered_df.columns:
        filtered_df = filtered_df[
            (filtered_df["Price"] >= price_range[0])
            & (filtered_df["Price"] <= price_range[1])
        ]

    if "Area" in filtered_df.columns:
        filtered_df = filtered_df[
            (filtered_df["Area"] >= area_range[0])
            & (filtered_df["Area"] <= area_range[1])
        ]

    # ===== KPIs =====
    st.subheader("📊 Key Metrics")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Total Properties", len(filtered_df))
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        avg_price = (
            filtered_df["Price"].mean()
            if "Price" in filtered_df.columns and not filtered_df.empty
            else 0
        )
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Avg Price", f"{avg_price:,.0f} EGP" if avg_price > 0 else "N/A")
        st.markdown("</div>", unsafe_allow_html=True)

    with col3:
        avg_area = (
            filtered_df["Area"].mean()
            if "Area" in filtered_df.columns and not filtered_df.empty
            else 0
        )
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Avg Area", f"{avg_area:.0f} m²" if avg_area > 0 else "N/A")
        st.markdown("</div>", unsafe_allow_html=True)

    with col4:
        if "Payment_Method" in filtered_df.columns and not filtered_df.empty:
            installment_count = (filtered_df["Payment_Method"] == "Installments").sum()
            installment_ratio = (
                (installment_count / len(filtered_df)) * 100
                if len(filtered_df) > 0
                else 0
            )
        else:
            installment_ratio = 0
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Installments", f"{installment_ratio:.1f}%")
        st.markdown("</div>", unsafe_allow_html=True)

    # ===== CHARTS =====
    st.subheader("📈 Analytics")
    fig7 = px.violin(
        filtered_df,
        "PropertyType",
        "Price",
        box=True,
        # points='all',
        color="Payment_Method",
        title="Price per m² Distribution by Property Type",
    )
    st.plotly_chart(fig7, use_container_width=True)
    # Chart 1: توزيع العقارات حسب المدينة
    if not filtered_df.empty and "State" in filtered_df.columns:
        fig1 = px.bar(
            filtered_df["State"].value_counts().reset_index(),
            x="State",
            y="count",
            title="Properties Distribution by City",
            color="count",
            color_continuous_scale="Viridis",
        )
        st.plotly_chart(fig1, use_container_width=True)

    # Chart 2: العلاقة بين السعر والمساحة
    if len(filtered_df) > 1 and all(
        col in filtered_df.columns
        for col in ["Area", "Price", "PropertyType", "Bedrooms"]
    ):
        fig2 = px.scatter(
            filtered_df,
            x="Area",
            y="Price",
            color="PropertyType",
            size="Bedrooms",
            hover_name="State" if "State" in filtered_df.columns else None,
            hover_data=(
                ["Location", "Payment_Method", "Price_Per_M"]
                if all(
                    col in filtered_df.columns
                    for col in ["Location", "Payment_Method", "Price_Per_M"]
                )
                else None
            ),
            title="Price vs Area Analysis",
            labels={"Area": "Area (m²)", "Price": "Price (EGP)"},
        )
        st.plotly_chart(fig2, use_container_width=True)

    # Chart 3: متوسط سعر المتر حسب المنطقة
    if (
        not filtered_df.empty
        and "Location" in filtered_df.columns
        and "Price_Per_M" in filtered_df.columns
    ):
        col1, col2 = st.columns(2)
        with col1:
            avg_price_by_location = (
                filtered_df.groupby("Location").agg({"Price_Per_M": "mean"}).reset_index()
            )
            fig3 = px.bar(
                avg_price_by_location.sort_values("Price_Per_M", ascending=True).head(10),
                x="Location",
                y="Price_Per_M",
                title="Average Price Per m² by Location (Top 10) 'ASC'",
                color="Price_Per_M",
                color_continuous_scale="Plasma",
            )
            st.plotly_chart(fig3, use_container_width=True)
        with col2:
            avg_price_by_location_desc = (
                filtered_df.groupby("Location").agg({"Price_Per_M": "mean"}).reset_index()
            )
            fig4 = px.bar(
                avg_price_by_location_desc.sort_values("Price_Per_M", ascending=False).head(10),
                x="Location",
                y="Price_Per_M",
                title="Average Price Per m² by Location (Top 10) 'DESC'",
                color="Price_Per_M",
                color_continuous_scale="Plasma",
            )
            st.plotly_chart(fig4, use_container_width=True)

    if (
        not filtered_df.empty
        and "State" in filtered_df.columns
        and "Price_Per_M" in filtered_df.columns
    ):
        col1, col2 = st.columns(2)
        with col1:
            avg_price_by_location = (
                filtered_df.groupby("State").agg({"Price_Per_M": "mean"}).reset_index()
            )
            fig3 = px.bar(
                avg_price_by_location.sort_values("Price_Per_M", ascending=False).head(10),
                x="State",
                y="Price_Per_M",
                title="Average Price Per m² by State (Top 10) 'DESC'",
                color="Price_Per_M",
                color_continuous_scale="Plasma",
            )
            st.plotly_chart(fig3, use_container_width=True)
        with col2:
            avg_price_by_location = (
                filtered_df.groupby("State").agg({"Price_Per_M": "mean"}).reset_index()
            )
            fig3 = px.bar(
                avg_price_by_location.sort_values("Price_Per_M", ascending=True).head(10),
                x="State",
                y="Price_Per_M",
                title="Average Price Per m² by State (Top 10) 'ASC'",
                color="Price_Per_M",
                color_continuous_scale="Plasma",
            )
            st.plotly_chart(fig3, use_container_width=True)

    

    # ===== DATA TABLE =====
    st.subheader("📋 Property List")

    search_query = st.text_input(
        "🔍 Search properties...", placeholder="Type property name or location..."
    )

    if (
        search_query
        and "Title" in filtered_df.columns
        and "Location" in filtered_df.columns
    ):
        display_df = filtered_df[
            filtered_df["Title"]
            .astype(str)
            .str.contains(search_query, case=False, na=False)
            | filtered_df["Location"]
            .astype(str)
            .str.contains(search_query, case=False, na=False)
        ]
    else:
        display_df = filtered_df

    if not display_df.empty:
        available_columns = []
        for col in [
            "Title".format(),
            "PropertyType",
            "Price",
            "Location",
            "State",
            "Bedrooms",
            "Area",
            "Price_Per_M",
            "Down_Payment",
            "Payment_Method",
        ]:
            if col in display_df.columns:
                available_columns.append(col)

        st.dataframe(
            display_df[available_columns].head(20),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No properties match your filters. Try adjusting them.")

# with tab2:  # Price Predictor
#     st.subheader("💰 AI Price Predictor")

#     col1, col2 = st.columns([2, 1])

#     with col1:
#         st.write(
#             """
#         ### توقع سعر العقار

#         أدخل مواصفات العقار للحصول على تقدير للسعر المتوقع:
#         """
#         )

#         area = st.number_input(
#             "المساحة (م²)", min_value=50, max_value=1000, value=120, step=10
#         )
#         bedrooms = st.selectbox("عدد الغرف", [1, 2, 3, 4, 5, 6], index=2)
#         bathrooms = st.selectbox("عدد الحمامات", [1, 2, 3, 4], index=1)

#         if "Location" in df.columns:
#             locations = sorted(df["State"].dropna().unique())
#             selected_location = st.selectbox("المنطقة", ["عام"] + locations)
#         else:
#             selected_location = None

#         if st.button("🔮 توقع السعر", use_container_width=True):
#             with st.spinner("جاري تحليل البيانات وتوقع السعر..."):
#                 model_info = train_price_model(df)

#                 if model_info:
#                     model, features = model_info
#                     predicted_price = predict_property_price(
#                         model, features, area, bedrooms, bathrooms
#                     )

#                     if predicted_price:
#                         st.markdown(
#                             f'<div class="prediction-card">', unsafe_allow_html=True
#                         )
#                         st.metric("💰 السعر المتوقع", f"{predicted_price:,.0f} EGP")
#                         st.markdown("</div>", unsafe_allow_html=True)

#                         # مقارنة مع المتوسط
#                         if "Price_Per_M" in df.columns:
#                             avg_price_m2 = df["Price_Per_M"].mean()
#                             avg_price = area * avg_price_m2
#                             diff = predicted_price - avg_price
#                             diff_percent = (
#                                 (diff / avg_price) * 100 if avg_price > 0 else 0
#                             )

#                             st.info(
#                                 f"""
#                             **المقارنة مع المتوسط:**
#                             - متوسط سعر المتر: {avg_price_m2:,.0f} EGP
#                             - السعر المتوقع للمساحة: {avg_price:,.0f} EGP
#                             - الفرق: {diff:,.0f} EGP ({diff_percent:+.1f}%)
#                             """
#                             )
#                     else:
#                         st.error("تعذر توقع السعر. حاول مرة أخرى.")
#                 else:
#                     st.warning("لا توجد بيانات كافية للتدريب. أضف المزيد من العقارات.")

#     with col2:

#         st.write("### 📊 إحصائيات السوق")
#         if len(df) > 0:
#             if "Price" in df.columns:
#                 st.metric("متوسط السعر", f"{df['Price'].mean():,.0f} EGP")
#             if "Price_Per_M" in df.columns:
#                 st.metric("متوسط سعر المتر", f"{df['Price_Per_M'].mean():,.0f} EGP")
#             if "Area" in df.columns:
#                 st.metric("متوسط المساحة", f"{df['Area'].mean():.0f} م²")

# with tab3:  # AI Recommendations
#     st.subheader("🤖 AI Property Recommendations")

#     if len(df) > 0:
#         # اختيار عقار للبدء
#         property_options = []
#         if "Title" in df.columns:
#             for idx, row in df.head(50).iterrows():  # عرض أول 50 عقار فقط للسرعة
#                 title = row["Title"] if pd.notna(row["Title"]) else f"Property #{idx}"
#                 location = (
#                     row["Location"]
#                     if "Location" in row and pd.notna(row["Location"])
#                     else ""
#                 )
#                 price = row["Price"] if "Price" in row and pd.notna(row["Price"]) else 0
#                 property_options.append(
#                     (idx, f"{title} - {location} - {price:,.0f} EGP")
#                 )

#         if property_options:
#             selected_property_idx = st.selectbox(
#                 "اختر عقاراً للعثور على مشابهاته",
#                 [f"#{idx}: {text}" for idx, text in property_options],
#             )

#             # استخراج ID العقار المختار
#             try:
#                 property_id = int(selected_property_idx.split(":")[0].replace("#", ""))
#             except:
#                 property_id = 0

#             if st.button("🔍 ابحث عن عقارات مشابهة", use_container_width=True):
#                 with st.spinner("جاري البحث عن عقارات مشابهة..."):
#                     recommendations = get_recommendations(df, property_id, n=5)

#                     if len(recommendations) > 0:
#                         st.success(f"✅ وجدنا {len(recommendations)} عقاراً مشابهاً")

#                         for idx, row in recommendations.iterrows():
#                             with st.expander(
#                                 f"🏠 {row.get('Title', f'عقار #{idx}')}", expanded=False
#                             ):
#                                 col_a, col_b = st.columns(2)

#                                 with col_a:
#                                     if "Price" in row:
#                                         st.metric("السعر", f"{row['Price']:,.0f} EGP")
#                                     if "Area" in row:
#                                         st.metric("المساحة", f"{row['Area']} م²")

#                                 with col_b:
#                                     if "Location" in row:
#                                         st.write(f"**الموقع:** {row['Location']}")
#                                     if "Bedrooms" in row:
#                                         st.write(f"**الغرف:** {row['Bedrooms']}")
#                                     if "PropertyType" in row:
#                                         st.write(f"**النوع:** {row['PropertyType']}")
#                     else:
#                         st.info("لم يتم العثور على عقارات مشابهة. حاول مع عقار آخر.")
#         else:
#             st.info("أضف بيانات للعقارات لعرض التوصيات.")
#     else:
#         st.info("لا توجد بيانات لعرض التوصيات.")

with tab2:  # Market Insights
    st.subheader("📈 Market Insights & Analytics")

    insights = calculate_market_insights(df)

    if insights:
        # البطاقات الرئيسية
        col1, col2, col3 = st.columns(3)

        with col1:
            if "price_stats" in insights:
                st.metric(
                    "💰 متوسط السعر", f"{insights['price_stats']['mean']:,.0f} EGP"
                )

        with col2:
            if "price_per_m_stats" in insights:
                st.metric(
                    "📏 متوسط سعر المتر",
                    f"{insights['price_per_m_stats']['mean']:,.0f} EGP",
                )

        with col3:
            if "payment_distribution" in insights:
                installment_rate = insights["payment_distribution"].get(
                    "Installments", 0
                )
                st.metric("💳 نسبة التقسيط", f"{installment_rate:.1f}%")

        st.markdown("---")

        f = px.histogram(
        filtered_df,
        "Price",
        text_auto=True,
        color_discrete_sequence=["#292C60" ],
        title="Price Distribution",
        )
        st.plotly_chart(f, use_container_width=True)

        # تحليل المناطق
        col4, col5 = st.columns(2)

        with col4:
            if "expensive_areas" in insights:
                st.write("### 🏙️ أغلى المناطق")
                for area, price in insights["expensive_areas"].items():
                    st.write(f"**{area}:** {price:,.0f} EGP/م²")

        with col5:
            if "affordable_areas" in insights:
                st.write("### 💰 أكثر المناطق معقولة")
                for area, price in insights["affordable_areas"].items():
                    st.write(f"**{area}:** {price:,.0f} EGP/م²")

        # avg_price = (
        #     filtered_df.groupby(["State", "Location"])["Price"].mean().reset_index()
        # )
        # fig11 = px.treemap(
        #     avg_price, path=["State", "Location"], values="Price" , title="متوسط السعر حسب المنطقة"
        # ).update_layout(margin=dict(t=20, l=25, r=25, b=20))
        # st.plotly_chart(fig11, use_container_width=True)
        
        avg_price1 = (
            filtered_df.groupby(["State", "Location"])["Price_Per_M"]
            .mean()
            .reset_index()
        )

        # حساب إحصائيات إضافية
        stats_df = filtered_df.groupby(["State", "Location"]).agg({
            "Price_Per_M": ["mean", "count", "std"],
            "Price": "mean",
            "Area": "mean"
        }).reset_index()

        # تسطيح MultiIndex columns
        stats_df.columns = ['_'.join(col).strip('_') if col[1] else col[0] for col in stats_df.columns.values]

        # دمج البيانات
        avg_price1 = avg_price1.merge(
            stats_df[["State", "Location", "Price_Per_M_count", "Price_Per_M_std", "Price_mean", "Area_mean"]],
            on=["State", "Location"],
            how="left"
        )

        # إعادة تسمية الأعمدة
        avg_price1 = avg_price1.rename(columns={
            "Price_Per_M": "Price_Per_M_mean",
            "Price_mean": "Avg_Price",
            "Area_mean": "Avg_Area",
            "Price_Per_M_count": "Property_Count",
            "Price_Per_M_std": "Price_Std"
        })

        # خريطة الشجرة مع hover مخصص
        fig12 = px.treemap(
            avg_price1,
            path=["State", "Location"],
            values="Price_Per_M_mean",
            title="State Distribution",
            color="Price_Per_M_mean",
            # color_continuous_scale="RdYlGn_r",  # الأحمر للأعلى، الأخضر للأدنى
            hover_data={
                "Price_Per_M_mean": ":.0f",  # تنسيق الأرقام
                "Avg_Price": ":.0f",
                "Avg_Area": ":.0f",
                "Property_Count": True,
                "Price_Std": ":.0f"
            },
            custom_data=["Price_Per_M_mean", "Avg_Price", "Avg_Area", "Property_Count", "Price_Std"]
        )

        # تحديث hover template
        fig12.update_traces(
            hovertemplate="<b>%{label}</b><br>" +
                        "-------------------<br>" +
                        "📊 <b>متوسط سعر المتر:</b> %{customdata[0]:,.0f} EGP<br>" +
                        "💰 <b>متوسط السعر الكلي:</b> %{customdata[1]:,.0f} EGP<br>" +
                        "📐 <b>متوسط المساحة:</b> %{customdata[2]:,.0f} م²<br>" +
                        "🏠 <b>عدد العقارات:</b> %{customdata[3]:,.0f}<br>" +
                        "📈 <b>انحراف المعياري للأسعار:</b> %{customdata[4]:,.0f} EGP<br>" +
                        "-------------------<br>" +
                        "<i>انقر للتكبير/التصغير</i>"
        )

        # تحديث التخطيط
        fig12.update_layout(
            margin=dict(t=40, l=25, r=25, b=20),
            coloraxis_colorbar=dict(
                title="سعر المتر (EGP)",
                thickness=20,
                len=0.75
            )
        )

        st.plotly_chart(fig12, use_container_width=True)

        # توزيع أنواع العقارات
        if "property_distribution" in insights:
            st.write("### 🏘️ توزيع أنواع العقارات")

            prop_data = pd.DataFrame(
                {
                    "Type": list(insights["property_distribution"].keys()),
                    "Percentage": list(insights["property_distribution"].values()),
                }
            )

            fig = px.pie(
                prop_data,
                values="Percentage",
                names="Type",
                title="توزيع أنواع العقارات في السوق",
            )
            st.plotly_chart(fig, use_container_width=True)
            # احسب متوسط السعر لكل نوع
            avg_price_by_type = filtered_df.groupby('PropertyType')['Price'].mean().reset_index()
            col7, col8 = st.columns(2)
            with col7:
                fig8 = px.pie(
                    avg_price_by_type,
                    values='Price',  # متوسط السعر لكل نوع
                    names='PropertyType',
                    title="متوسط سعر العقارات حسب النوع",
                )
                st.plotly_chart(fig8, use_container_width=True)
            avg_pricem_by_type = (
                filtered_df.groupby("PropertyType")["Price_Per_M"].mean().reset_index()
            )
            with col8:
                fig9 = px.pie(
                    avg_pricem_by_type,
                    values="Price_Per_M",  # متوسط السعر لكل نوع
                    names="PropertyType",
                    title="متوسط سعر المتر العقارات حسب النوع",
                )
                st.plotly_chart(fig9, use_container_width=True)


# ========== SIDEBAR COMMON ELEMENTS ==========
# معلومات إضافية في الـ Sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("📈 Quick Stats")

if not df.empty:
    if "Price" in df.columns:
        st.sidebar.metric("Total Value", f"{df['Price'].sum():,.0f} EGP")

    if "Price_Per_M" in df.columns:
        avg_price_m2 = df["Price_Per_M"].mean()
        st.sidebar.metric(
            "Avg Price/m²", f"{avg_price_m2:,.0f} EGP" if avg_price_m2 > 0 else "N/A"
        )

    if "PropertyType" in df.columns:
        st.sidebar.metric("Property Types", df["PropertyType"].nunique())

# معلومات التحديث التلقائي
st.sidebar.markdown("---")
st.sidebar.subheader("🔄 Auto-Update Status")

st.sidebar.info(
    f"""
**Last Update:** {st.session_state.get('last_update', 'Checking...')}

**Properties:** {len(df):,}
**AI Features:** Enabled
**Next Update:** 4:00 AM Egypt Time
"""
)

# معلومات النظام
st.sidebar.markdown("---")


# Footer في الأسفل
st.markdown("---")
st.markdown(
    f"""
<div style="text-align: center; padding: 20px; color: #666;">
    <p>🏠 Real Estate Dashboard | Powered by Mohamed Elsify</p>
    <p style="font-size: 0.9em;">Version 1.0 | Last update: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
</div>
""",
    unsafe_allow_html=True,
)
