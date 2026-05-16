# app.py - نسخة محدثة مع API وتصميم محسن - Merged with Desktop Graphs

import streamlit as st
import pandas as pd
from plotly import express as px
from plotly import graph_objects as go
from datetime import datetime, timedelta
import requests
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
import json
import io
import base64

# إعداد الصفحة
st.set_page_config(
    page_title="Real Estate Egypt",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ========== API Configuration ==========
API_BASE_URL = "http://65.75.201.173:8000"
API_PROPERTIES = f"{API_BASE_URL}/real-estate/properties"
API_INSIGHTS = f"{API_BASE_URL}/real-estate/insights/market"
API_RECOMMENDATIONS = f"{API_BASE_URL}/real-estate/recommendations"
API_AREA_INTELLIGENCE = f"{API_BASE_URL}/real-estate/area-intelligence"
API_PREDICT = f"{API_BASE_URL}/real-estate/predict"
API_STATS = f"{API_BASE_URL}/real-estate/stats/summary"

# ========== Custom CSS ==========
st.markdown(
    """
<style>
    /* Main title */
    .main-title {
        text-align: center;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        padding: 20px;
        font-size: 3rem;
        font-weight: bold;
    }
    
    /* Metric cards */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        margin: 10px 0;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        transition: transform 0.3s;
    }
    .metric-card:hover {
        transform: translateY(-5px);
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 10px 20px;
        font-weight: bold;
        transition: all 0.3s;
    }
    .stButton > button:hover {
        transform: scale(1.02);
        box-shadow: 0 4px 15px rgba(102,126,234,0.4);
    }
    
    /* Dataframe styling */
    .dataframe {
        border-radius: 10px;
        overflow: hidden;
    }
    
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        padding: 10px 20px;
        color: white;
    }
    
    /* Info boxes */
    .success-box {
        background: linear-gradient(135deg, #43cea2 0%, #185a9d 100%);
        padding: 15px;
        border-radius: 10px;
        color: white;
        margin: 10px 0;
    }
    .warning-box {
        background: linear-gradient(135deg, #ff4e50 0%, #f9d423 100%);
        padding: 15px;
        border-radius: 10px;
        color: white;
        margin: 10px 0;
    }
    
    /* Custom divider */
    .custom-divider {
        height: 3px;
        background: linear-gradient(90deg, #667eea, #764ba2, #667eea);
        margin: 20px 0;
        border-radius: 3px;
    }
    
    /* Gauge container */
    .gauge-container {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 20px;
        border-radius: 15px;
        margin: 10px 0;
    }
</style>
""",
    unsafe_allow_html=True,
)


# ========== API Functions ==========
@st.cache_data(ttl=300)
def load_data_from_api(filters=None):
    """تحميل البيانات من API"""
    try:
        params = filters or {}
        response = requests.get(API_PROPERTIES, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            return pd.DataFrame(data.get("properties", []))
        else:
            st.error(f"❌ API Error: {response.status_code}")
            return pd.DataFrame()
    except Exception as e:
        st.warning(f"⚠️ Could not connect to API: {str(e)[:100]}")
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def load_area_intelligence():
    """تحميل بيانات ذكاء المناطق من API"""
    try:
        response = requests.get(API_AREA_INTELLIGENCE, timeout=30)
        if response.status_code == 200:
            return pd.DataFrame(response.json())
        else:
            return pd.DataFrame()
    except:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_market_insights():
    """تحميل رؤى السوق من API"""
    try:
        response = requests.get(API_INSIGHTS, timeout=30)
        if response.status_code == 200:
            return response.json()
        return {}
    except:
        return {}


@st.cache_data(ttl=300)
def load_stats_summary():
    """تحميل الإحصائيات من API"""
    try:
        response = requests.get(API_STATS, timeout=30)
        if response.status_code == 200:
            return response.json()
        return {}
    except:
        return {}


# ========== Helper Functions ==========
def calculate_price_per_m(price, area):
    return price / area if area > 0 else 0


def get_buy_score_color(score):
    if score >= 80:
        return "🟢"
    elif score >= 65:
        return "🟡"
    elif score >= 50:
        return "🟠"
    else:
        return "🔴"


def normalize_series(series):
    """دالة تطبيع محلية"""
    if series.max() == series.min():
        return 0.5
    return (series - series.min()) / (series.max() - series.min())


# ========== Buy Score & Treemap Functions (adapted from desktop file) ==========
def enrich_with_area_features(df, area_df):
    """ربط بيانات العقارات بخصائص المنطقة"""
    df = df.copy()
    if area_df.empty:
        return df

    # Map area intelligence columns - try matching on state or location
    area_numeric_cols = [
        "near_sea", "schools_quality", "services_level",
        "transportation", "investment_potential", "resale_liquidity", "area_score"
    ]

    # Check if area_df has the expected columns
    area_cols_present = [c for c in area_numeric_cols if c in area_df.columns]
    if not area_cols_present:
        return df

    # Try to merge on state or location
    merge_col = None
    if "area_name" in area_df.columns:
        merge_col = "area_name"
    elif "state" in area_df.columns:
        merge_col = "state"
    elif "location" in area_df.columns:
        merge_col = "location"

    if merge_col and merge_col in df.columns:
        df = df.merge(area_df, left_on=merge_col, right_on=merge_col, how="left", suffixes=("", "_area"))

    # Fill missing area intelligence values with defaults
    for col in area_numeric_cols:
        if col in df.columns:
            df[col] = df[col].fillna(df[col].median() if not df[col].isna().all() else 3)
        else:
            if col == "area_score":
                df[col] = 70
            elif col == "near_sea":
                df[col] = 0
            else:
                df[col] = 3

    return df


@st.cache_resource(ttl=3600)
def train_model_once(df):
    """تدريب النموذج مرة واحدة مع دمج ذكاء المناطق"""
    if df.empty or len(df) < 50:
        return None, [], {}

    ml_df = df.copy()

    # Load & Merge Area Intelligence
    area_df = load_area_intelligence()
    ml_df = enrich_with_area_features(ml_df, area_df)

    # Payment Method Encoding
    if "payment_method" in ml_df.columns:
        ml_df["payment_code"] = (
            ml_df["payment_method"]
            .map({"Cash": 0, "Installments": 1, "نقدي": 0, "تقسيط": 1})
            .fillna(0)
        )

    # Property Type Encoding
    property_map = {}
    if "property_type" in ml_df.columns:
        property_types = ml_df["property_type"].dropna().unique()
        property_map = {pt: i for i, pt in enumerate(property_types)}
        ml_df["property_type_code"] = ml_df["property_type"].map(property_map)

    # Feature Selection
    numeric_features = []
    candidates = [
        "area", "bedrooms", "bathrooms", "price_per_m",
        "payment_code", "property_type_code",
        "near_sea", "schools_quality", "services_level",
        "transportation", "investment_potential", "resale_liquidity", "area_score",
    ]

    for col in candidates:
        if col in ml_df.columns:
            numeric_features.append(col)

    ml_df = ml_df[numeric_features + ["price"]].dropna()

    if len(ml_df) < 50:
        return None, [], {}

    X = ml_df[numeric_features]
    y = ml_df["price"]

    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=45
        )

        rf_model = RandomForestRegressor(
            n_estimators=150, max_depth=20, random_state=47, n_jobs=-1
        )
        rf_model.fit(X_train, y_train)

        y_pred = rf_model.predict(X_test)
        mae = mean_absolute_error(y_test, y_pred)

        st.session_state["model_mae"] = round(mae, 2)

        return rf_model, numeric_features, property_map

    except Exception as e:
        st.sidebar.error(f"❌ Model training error: {str(e)[:100]}")
        return None, [], {}


def create_treemap_data(filtered_df, model, features, prop_map):
    """إنشاء بيانات Treemap مع Buy Score"""
    if filtered_df.empty:
        return pd.DataFrame()

    # Merge area intelligence
    area_df = load_area_intelligence()
    filtered_df = enrich_with_area_features(filtered_df, area_df)

    # Aggregations by State and Location
    stats_df = (
        filtered_df.groupby(["state", "location"])
        .agg({"price_per_m": ["mean", "count", "std"], "price": "mean", "area": "mean"})
        .reset_index()
    )
    stats_df.columns = [
        "_".join(col).strip("_") if col[1] else col[0]
        for col in stats_df.columns.values
    ]

    # Rename columns for clarity
    stats_df = stats_df.rename(
        columns={
            "price_per_m_mean": "Price_Per_M_mean",
            "price_mean": "Avg_Price",
            "area_mean": "Avg_Area",
            "price_per_m_count": "Property_Count",
            "price_per_m_std": "Price_Std",
        }
    )

    # Fill NaN Std with 0
    stats_df["Price_Std"] = stats_df["Price_Std"].fillna(0)

    # Calculate area intelligence scores per location
    area_stats = (
        filtered_df.groupby(["state", "location"])
        .agg({
            "area_score": "mean",
            "investment_potential": "mean",
            "resale_liquidity": "mean",
            "schools_quality": "mean",
            "services_level": "mean",
            "transportation": "mean",
            "near_sea": "mean",
        })
        .reset_index()
    )

    # Merge area stats
    stats_df = stats_df.merge(area_stats, on=["state", "location"], how="left")

    # Calculate Area Intelligence Score
    def calculate_area_intelligence(row):
        scores = []
        weights = []

        if pd.notna(row.get("area_score")):
            scores.append(row["area_score"] / 100)
            weights.append(0.4)
        if pd.notna(row.get("investment_potential")):
            scores.append(row["investment_potential"] / 5)
            weights.append(0.3)
        if pd.notna(row.get("resale_liquidity")):
            scores.append(row["resale_liquidity"] / 5)
            weights.append(0.2)
        if pd.notna(row.get("schools_quality")):
            scores.append(row["schools_quality"] / 5)
            weights.append(0.1)

        if scores and weights:
            weighted_sum = sum(s * w for s, w in zip(scores, weights))
            total_weight = sum(weights)
            return weighted_sum / total_weight
        return 0.5

    stats_df["Area_Intelligence_Score"] = stats_df.apply(calculate_area_intelligence, axis=1)

    # Prediction Logic using Cached Model
    if model is not None and features:
        try:
            fair_prices = []
            for idx, row in stats_df.iterrows():
                input_data = {
                    "area": row["Avg_Area"],
                    "bedrooms": 3,
                    "bathrooms": 2,
                    "price_per_m": row["Price_Per_M_mean"],
                    "payment_code": 0,
                    "property_type_code": prop_map.get("Apartment", 0),
                    "near_sea": row.get("near_sea", 0),
                    "schools_quality": row.get("schools_quality", 3),
                    "services_level": row.get("services_level", 3),
                    "transportation": row.get("transportation", 3),
                    "investment_potential": row.get("investment_potential", 3),
                    "resale_liquidity": row.get("resale_liquidity", 3),
                    "area_score": row.get("area_score", 70),
                }

                pred_vector = [input_data.get(f, 0) for f in features]
                predicted_price = model.predict([pred_vector])[0]
                fair_prices.append(predicted_price)

            stats_df["Fair_Price"] = fair_prices
        except Exception as e:
            stats_df["Fair_Price"] = stats_df["Price_Per_M_mean"] * stats_df["Avg_Area"]
    else:
        stats_df["Fair_Price"] = stats_df["Price_Per_M_mean"] * stats_df["Avg_Area"]

    # Scoring Logic
    price_min = stats_df["Price_Per_M_mean"].min()
    price_max = stats_df["Price_Per_M_mean"].max()
    stats_df["Price_Score"] = (
        1 - ((stats_df["Price_Per_M_mean"] - price_min) / (price_max - price_min))
        if price_max != price_min else 0.5
    )

    std_min = stats_df["Price_Std"].min()
    std_max = stats_df["Price_Std"].max()
    stats_df["Stability_Score"] = (
        1 - ((stats_df["Price_Std"] - std_min) / (std_max - std_min))
        if std_max != std_min else 0.5
    )

    area_min = stats_df["Avg_Area"].min()
    area_max = stats_df["Avg_Area"].max()
    stats_df["Area_Size_Score"] = (
        (stats_df["Avg_Area"] - area_min) / (area_max - area_min)
        if area_max != area_min else 0.5
    )

    count_min = stats_df["Property_Count"].min()
    count_max = stats_df["Property_Count"].max()
    stats_df["Supply_Score"] = (
        (stats_df["Property_Count"] - count_min) / (count_max - count_min)
        if count_max != count_min else 0.5
    )

    # Buy Score Calculation
    stats_df["Buy_Score"] = (
        stats_df["Price_Score"] * 0.30
        + stats_df["Stability_Score"] * 0.20
        + stats_df["Supply_Score"] * 0.15
        + stats_df["Area_Size_Score"] * 0.10
        + stats_df["Area_Intelligence_Score"] * 0.25
    ) * 100

    stats_df["Buy_Score"] = stats_df["Buy_Score"].clip(0, 100)

    # Value Score adjustment
    if "Fair_Price" in stats_df.columns:
        stats_df["Value_Score"] = stats_df.apply(
            lambda row: (
                100 * (1 - (row["Avg_Price"] / row["Fair_Price"]))
                if row["Fair_Price"] > 0 else 50
            ),
            axis=1,
        ).clip(0, 100)

        stats_df["Buy_Score"] = (
            stats_df["Buy_Score"] * 0.7 + stats_df["Value_Score"] * 0.3
        ).clip(0, 100)

    # Classification and Recommendations
    def buy_label(score):
        if score >= 80:
            return "🟢 فرصة شراء ممتازة"
        elif score >= 65:
            return "🟡 خيار جيد"
        elif score >= 50:
            return "🟠 متوسط - يحتاج تفاوض"
        else:
            return "🔴 سعر مرتفع"

    stats_df["Buy_Label"] = stats_df["Buy_Score"].apply(buy_label)

    stats_df["Recommendation"] = stats_df.apply(
        lambda row: (
            "🏆 موصى به بشدة" if row["Buy_Score"] >= 80
            else "👍 جيد" if row["Buy_Score"] >= 65
            else "🤔 متوسط" if row["Buy_Score"] >= 50
            else "⚠️ غير موصى به"
        ),
        axis=1,
    )

    return stats_df


def create_buy_score_gauge(score):
    """إنشاء مقياس Buy Score"""
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"suffix": " / 100", "font": {"size": 24, "color": "white"}},
            title={"text": "🏷️ Buy Score", "font": {"size": 18, "color": "white"}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "white", "tickfont": {"color": "white"}},
                "bar": {"color": "#1f77b4"},
                "bgcolor": "rgba(0,0,0,0)",
                "steps": [
                    {"range": [0, 50], "color": "#ff4d4d"},
                    {"range": [50, 65], "color": "#ffa500"},
                    {"range": [65, 80], "color": "#ffd700"},
                    {"range": [80, 100], "color": "#2ecc71"},
                ],
                "threshold": {
                    "line": {"color": "black", "width": 4},
                    "thickness": 0.75,
                    "value": score,
                },
            },
        )
    )

    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": "white"},
    )

    return fig


def get_purchase_recommendations(filtered_df):
    """توليد توصيات الشراء"""
    recommendations = []
    try:
        if not filtered_df.empty and "bedrooms" in filtered_df.columns:
            room_counts = filtered_df["bedrooms"].value_counts()
            if not room_counts.empty:
                most_popular = room_counts.idxmax()
                recommendations.append(f"- الشقق {most_popular} غرف هي الأكثر طلبًا حاليًا")
    except:
        recommendations.append("- الشقق 3-4 غرف هي الأكثر طلبًا بشكل عام")
    recommendations.append("- لو ميزانيتك متوسطة → ركّز على المناطق ذات سعر متر أقل من المتوسط العام")
    recommendations.append("- تجنّب المناطق ذات الانحراف السعري العالي (عدم استقرار الأسعار)")
    recommendations.append("- Fair Price هي مؤشر جيد لتقييم السعر العادل للعقار")
    recommendations.append("- Buy Score يساعدك في اختيار المناطق ذات الفرص الأفضل للشراء")
    return recommendations


def calculate_area_insights(filtered_df):
    """حساب رؤى المساحة"""
    if filtered_df.empty or "area" not in filtered_df.columns or "price" not in filtered_df.columns:
        return "120 و 180 متر", "بمعدل أسرع"
    try:
        area_counts, area_bins = np.histogram(filtered_df["area"].dropna(), bins=10)
        max_density_idx = np.argmax(area_counts)
        best_area_min = area_bins[max_density_idx]
        best_area_max = area_bins[max_density_idx + 1]
        best_area_text = f"{int(best_area_min)} و {int(best_area_max)} متر"
    except:
        best_area_text = "120 و 180 متر"
    try:
        median_area = filtered_df["area"].median()
        small_apartments = filtered_df[filtered_df["area"] <= median_area]
        large_apartments = filtered_df[filtered_df["area"] > median_area]
        if not small_apartments.empty and not large_apartments.empty:
            small_price_per_m = small_apartments["price"].mean() / small_apartments["area"].mean()
            large_price_per_m = large_apartments["price"].mean() / large_apartments["area"].mean()
            price_increase_rate = ((large_price_per_m - small_price_per_m) / small_price_per_m) * 100
            price_rate_text = f"{price_increase_rate:.1f}%" if price_increase_rate > 0 else "بمعدل أسرع"
        else:
            price_rate_text = "بمعدل أسرع"
    except:
        price_rate_text = "بمعدل أسرع"
    return best_area_text, price_rate_text


def calculate_market_insights(df):
    """حساب رؤى السوق"""
    insights = {}
    if len(df) == 0:
        return insights
    if "price" in df.columns:
        insights["price_stats"] = {
            "mean": df["price"].mean(),
            "median": df["price"].median(),
            "min": df["price"].min(),
            "max": df["price"].max(),
        }
    if "price_per_m" in df.columns:
        insights["price_per_m_stats"] = {
            "mean": df["price_per_m"].mean(),
            "median": df["price_per_m"].median(),
        }
    if "location" in df.columns and "price_per_m" in df.columns:
        location_prices = df.groupby("location")["price_per_m"].mean().sort_values(ascending=False)
        insights["expensive_areas"] = location_prices.head(5).to_dict()
        insights["affordable_areas"] = location_prices.tail(5).to_dict()
    if "property_type" in df.columns:
        property_dist = df["property_type"].value_counts(normalize=True) * 100
        insights["property_distribution"] = property_dist.to_dict()
    if "payment_method" in df.columns:
        payment_dist = df["payment_method"].value_counts(normalize=True) * 100
        insights["payment_distribution"] = payment_dist.to_dict()
    return insights


def export_to_csv(df):
    """تصدير البيانات إلى CSV"""
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_str = csv_buffer.getvalue()
    b64 = base64.b64encode(csv_str.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="real_estate_data.csv">📥 Download CSV File</a>'
    return href


def export_to_excel(df):
    """تصدير البيانات إلى Excel"""
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Real Estate')
    excel_buffer.seek(0)
    b64 = base64.b64encode(excel_buffer.read()).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="real_estate_data.xlsx">📥 Download Excel File</a>'
    return href


# ========== Dashboard Header ==========
st.markdown(
    '<h1 class="main-title">🏠 Real Estate Egypt Dashboard</h1>', unsafe_allow_html=True
)
st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/color/96/real-estate.png", width=80)
    st.markdown("## 🔍 Filters")

    # Load data for filters
    with st.spinner("Loading data..."):
        df_full = load_data_from_api()

    # Initialize filter variables with defaults
    selected_city = "All"
    selected_type = "All"
    selected_bedrooms = "All"
    selected_bathrooms = "All"
    selected_payment = "All"
    price_range = None
    area_range = None

    if not df_full.empty:
        # Filter controls
        property_types = (
            ["All"] + sorted(df_full["property_type"].dropna().unique().tolist())
            if "property_type" in df_full.columns
            else ["All"]
        )
        selected_type = st.selectbox("🏘️ Property Type", property_types)

        cities = (
            ["All"] + sorted(df_full["state"].dropna().unique().tolist())
            if "state" in df_full.columns
            else ["All"]
        )
        selected_city = st.selectbox("📍 State/City", cities)

        if "bedrooms" in df_full.columns:
            bed_options = ["All"] + sorted(
                df_full["bedrooms"].dropna().unique().tolist()
            )
            selected_bedrooms = st.selectbox("🛏️ Bedrooms", bed_options)

        if "bathrooms" in df_full.columns:
            bath_options = ["All"] + sorted(
                df_full["bathrooms"].dropna().unique().tolist()
            )
            selected_bathrooms = st.selectbox("🚽 Bathrooms", bath_options)

        if "price" in df_full.columns:
            price_min = int(df_full["price"].min())
            price_max = int(df_full["price"].max())
            price_range = st.slider(
                "💰 Price Range (EGP)",
                price_min,
                price_max,
                (price_min, price_max),
                format="%d",
            )

        if "area" in df_full.columns:
            area_min = int(df_full["area"].min())
            area_max = int(df_full["area"].max())
            area_range = st.slider(
                "📐 Area Range (m²)", area_min, area_max, (area_min, area_max)
            )

        payment_methods = (
            ["All"] + sorted(df_full["payment_method"].dropna().unique().tolist())
            if "payment_method" in df_full.columns
            else ["All"]
        )
        selected_payment = st.selectbox("💳 Payment Method", payment_methods)

    st.markdown("---")

    # Stats Summary
    st.markdown("## 📊 Quick Stats")
    stats = load_stats_summary()
    if stats:
        st.metric("🏠 Total Properties", f"{stats.get('total_properties', 0):,}")
        st.metric("💰 Avg Price", f"{stats.get('average_price', 0):,.0f} EGP")
        st.metric("📐 Avg Area", f"{stats.get('average_area', 0):.0f} m²")

    st.markdown("---")
    st.caption(f"🔄 Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# Main content - 4 tabs now
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "📈 Market Insights", "🤖 AI Predictions", "⏰ Time Analysis"])

# ========== Tab 1: Dashboard ==========
with tab1:
    # Build filters
    filters = {}
    if selected_city != "All":
        filters["state"] = selected_city
    if selected_type != "All":
        filters["property_type"] = selected_type
    if selected_bedrooms != "All":
        filters["bedrooms"] = selected_bedrooms
    if selected_bathrooms != "All":
        filters["bathrooms"] = selected_bathrooms
    if price_range is not None:
        filters["min_price"] = price_range[0]
        filters["max_price"] = price_range[1]
    if area_range is not None:
        filters["min_area"] = area_range[0]
        filters["max_area"] = area_range[1]
    if selected_payment != "All":
        filters["payment_method"] = selected_payment

    # Load filtered data
    with st.spinner("Loading properties..."):
        df = load_data_from_api(filters)

    if df.empty:
        st.info("No properties found matching your filters. Try adjusting them.")
    else:
        # Key Metrics Row
        st.markdown("## 📊 Key Metrics")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown(
                """
            <div class="metric-card">
                <h3>🏠 Total Properties</h3>
                <h2>{:,}</h2>
            </div>
            """.format(len(df)),
                unsafe_allow_html=True,
            )

        with col2:
            avg_price = df["price"].mean() if "price" in df.columns else 0
            st.markdown(
                """
            <div class="metric-card">
                <h3>💰 Avg Price</h3>
                <h2>{:,.0f} EGP</h2>
            </div>
            """.format(avg_price),
                unsafe_allow_html=True,
            )

        with col3:
            avg_area = df["area"].mean() if "area" in df.columns else 0
            st.markdown(
                """
            <div class="metric-card">
                <h3>📐 Avg Area</h3>
                <h2>{:.0f} m²</h2>
            </div>
            """.format(avg_area),
                unsafe_allow_html=True,
            )

        with col4:
            installment_pct = (
                (df["payment_method"] == "Installments").mean() * 100
                if "payment_method" in df.columns
                else 0
            )
            st.markdown(
                """
            <div class="metric-card">
                <h3>💳 Installments</h3>
                <h2>{:.1f}%</h2>
            </div>
            """.format(installment_pct),
                unsafe_allow_html=True,
            )

        st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

        # Market Sentiment Indicator (from desktop file)
        # Train model for treemap data
        rf_model, model_features, prop_map = train_model_once(df)
        treemap_data = create_treemap_data(df, rf_model, model_features, prop_map)

        if not treemap_data.empty:
            avg_buy_score = treemap_data["Buy_Score"].mean()
            if avg_buy_score >= 65:
                st.markdown(
                    '<div class="success-box">✅ السوق مناسب للشراء حاليًا، استغل الفرص!</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div class="warning-box">⚠️ السوق عالى السعر حاليًا، خليك حذر في اختياراتك!</div>',
                    unsafe_allow_html=True,
                )

        # Charts Row 1
        col1, col2 = st.columns(2)

        with col1:
            if "state" in df.columns:
                state_counts = df["state"].value_counts().head(10)
                fig = px.bar(
                    x=state_counts.values,
                    y=state_counts.index,
                    orientation="h",
                    title="🏙️ Top 10 States by Properties",
                    color=state_counts.values,
                    color_continuous_scale="Viridis",
                    labels={"x": "Number of Properties", "y": "State"},
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, width='stretch')

        with col2:
            if "property_type" in df.columns:
                type_counts = df["property_type"].value_counts()
                fig = px.pie(
                    values=type_counts.values,
                    names=type_counts.index,
                    title="🏘️ Property Type Distribution",
                    color_discrete_sequence=px.colors.sequential.Viridis,
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, width='stretch')

        # Charts Row 2 - Violin plots (from desktop file)
        col1, col2 = st.columns(2)

        with col1:
            if "property_type" in df.columns and "price" in df.columns:
                fig_violin1 = px.violin(
                    df,
                    x="property_type",
                    y="price",
                    box=True,
                    color="payment_method" if "payment_method" in df.columns else None,
                    title="🎻 Price Distribution by Property Type",
                    labels={"property_type": "Property Type", "price": "Price (EGP)"},
                )
                fig_violin1.update_layout(height=400)
                st.plotly_chart(fig_violin1, width='stretch')

        with col2:
            if "payment_method" in df.columns and "price" in df.columns:
                fig_violin2 = px.violin(
                    df,
                    x="payment_method",
                    y="price",
                    box=True,
                    points="all",
                    color="payment_method",
                    title="🎻 Price Distribution by Payment Method",
                    labels={"payment_method": "Payment Method", "price": "Price (EGP)"},
                )
                fig_violin2.update_layout(height=400)
                st.plotly_chart(fig_violin2, width='stretch')

        # Charts Row 3 - Box plots (from desktop file)
        col1, col2 = st.columns(2)

        with col1:
            if "bedrooms" in df.columns and "price_per_m" in df.columns:
                fig_box1 = px.box(
                    df,
                    x="bedrooms",
                    y="price_per_m",
                    color="property_type" if "property_type" in df.columns else None,
                    title="📦 Price/m² Distribution by Bedrooms",
                    labels={"bedrooms": "Bedrooms", "price_per_m": "Price/m² (EGP)"},
                )
                fig_box1.update_layout(height=400)
                st.plotly_chart(fig_box1, width='stretch')

        with col2:
            if "bathrooms" in df.columns and "price_per_m" in df.columns:
                fig_box2 = px.box(
                    df,
                    x="bathrooms",
                    y="price_per_m",
                    color="property_type" if "property_type" in df.columns else None,
                    title="📦 Price/m² Distribution by Bathrooms",
                    labels={"bathrooms": "Bathrooms", "price_per_m": "Price/m² (EGP)"},
                )
                fig_box2.update_layout(height=400)
                st.plotly_chart(fig_box2, width='stretch')

        # Charts Row 4 - Scatter plot
        if "area" in df.columns and "price" in df.columns:
            fig = px.scatter(
                df,
                x="area",
                y="price",
                color="property_type" if "property_type" in df.columns else None,
                size="bedrooms" if "bedrooms" in df.columns else None,
                hover_data=["location", "state"],
                title="📈 Price vs Area Analysis",
                labels={"area": "Area (m²)", "price": "Price (EGP)"},
            )
            fig.update_layout(height=500)
            st.plotly_chart(fig, width='stretch')

        # Area Insights (from desktop file)
        best_area_text, price_rate_text = calculate_area_insights(df)
        st.markdown(
            f"**💡 ملاحظة مهمة:** أفضل قيمة مقابل السعر غالبًا بين **{best_area_text}**. المساحات الأكبر سعرها بيزيد **{price_rate_text}** من قيمتها الفعلية."
        )

        # Price per m² by Location (from desktop file)
        if "location" in df.columns and "price_per_m" in df.columns:
            st.markdown(
                "📍 **مقارنة المناطق** مش دايمًا المنطقة الأغلى هي الأفضل. في مناطق سعر المتر أقل لكن الطلب عليها أعلى، وده بيدي قيمة أفضل مقابل السعر."
            )
            col1, col2 = st.columns(2)
            with col1:
                avg_price_by_location = df.groupby("location")["price_per_m"].mean().reset_index()
                fig_loc_asc = px.bar(
                    avg_price_by_location.sort_values("price_per_m", ascending=True).head(10),
                    x="location",
                    y="price_per_m",
                    title="📍 Avg Price/m² by Location (ASC)",
                    color="price_per_m",
                    color_continuous_scale="Plasma",
                    labels={"location": "Location", "price_per_m": "Price/m² (EGP)"},
                )
                st.plotly_chart(fig_loc_asc, width='stretch')
            with col2:
                fig_loc_desc = px.bar(
                    avg_price_by_location.sort_values("price_per_m", ascending=False).head(10),
                    x="location",
                    y="price_per_m",
                    title="📍 Avg Price/m² by Location (DESC)",
                    color="price_per_m",
                    color_continuous_scale="Plasma",
                    labels={"location": "Location", "price_per_m": "Price/m² (EGP)"},
                )
                st.plotly_chart(fig_loc_desc, width='stretch')

        # Price per m² by State (from desktop file)
        if "state" in df.columns and "price_per_m" in df.columns:
            col1, col2 = st.columns(2)
            with col1:
                avg_price_by_state = df.groupby("state")["price_per_m"].mean().reset_index()
                fig_state_desc = px.bar(
                    avg_price_by_state.sort_values("price_per_m", ascending=False).head(10),
                    x="state",
                    y="price_per_m",
                    title="🏙️ Avg Price/m² by State (DESC)",
                    color="price_per_m",
                    color_continuous_scale="Plasma",
                    labels={"state": "State", "price_per_m": "Price/m² (EGP)"},
                )
                st.plotly_chart(fig_state_desc, width='stretch')
            with col2:
                fig_state_asc = px.bar(
                    avg_price_by_state.sort_values("price_per_m", ascending=True).head(10),
                    x="state",
                    y="price_per_m",
                    title="🏙️ Avg Price/m² by State (ASC)",
                    color="price_per_m",
                    color_continuous_scale="Plasma",
                    labels={"state": "State", "price_per_m": "Price/m² (EGP)"},
                )
                st.plotly_chart(fig_state_asc, width='stretch')

        # Property List with Pagination
        st.markdown("## 📋 Property List")

        search = st.text_input(
            "🔍 Search properties...", placeholder="Type location or property name..."
        )

        display_df = df.copy()
        if search:
            search_mask = display_df["location"].str.contains(search, case=False, na=False)
            if "title" in display_df.columns:
                search_mask |= display_df["title"].str.contains(search, case=False, na=False)
            display_df = display_df[search_mask]

        # Select columns to display
        cols_to_show = [
            "title", "property_type", "price", "location", "state",
            "bedrooms", "area", "payment_method", "price_per_m",
        ]
        available_cols = [c for c in cols_to_show if c in display_df.columns]

        # Pagination
        items_per_page = 20
        total_items = len(display_df)
        total_pages = max(1, (total_items + items_per_page - 1) // items_per_page)

        if "page_number" not in st.session_state:
            st.session_state.page_number = 1

        col1, col2, col3 = st.columns([1, 3, 1])
        with col1:
            if st.button("◀️ Previous", disabled=(st.session_state.page_number <= 1)):
                st.session_state.page_number = max(1, st.session_state.page_number - 1)
                st.rerun()
        with col2:
            st.markdown(
                f"<div style='text-align: center; padding: 8px;'>Page {st.session_state.page_number} of {total_pages} ({total_items:,} properties)</div>",
                unsafe_allow_html=True,
            )
        with col3:
            if st.button("Next ▶️", disabled=(st.session_state.page_number >= total_pages)):
                st.session_state.page_number = min(total_pages, st.session_state.page_number + 1)
                st.rerun()

        start_idx = (st.session_state.page_number - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, total_items)

        st.dataframe(
            display_df[available_cols].iloc[start_idx:end_idx],
            width='stretch',
            hide_index=True,
            column_config={
                "price": st.column_config.NumberColumn("Price", format="%d EGP"),
                "area": st.column_config.NumberColumn("Area", format="%.0f m²"),
                "price_per_m": st.column_config.NumberColumn("Price/m²", format="%d EGP"),
            },
        )

        # Data Export (medium priority)
        st.markdown("### 📥 Export Data")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(export_to_csv(display_df), unsafe_allow_html=True)
        with col2:
            st.markdown(export_to_excel(display_df), unsafe_allow_html=True)

# ========== Tab 2: Market Insights ==========
with tab2:
    st.markdown("## 📈 Market Insights & Analytics")

    insights = load_market_insights()

    if insights:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("💰 Average Price", f"{insights.get('avg_price', 0):,.0f} EGP")
        with col2:
            st.metric(
                "📏 Average Price/m²", f"{insights.get('avg_price_per_m', 0):,.0f} EGP"
            )
        with col3:
            st.metric("🏠 Total Properties", f"{insights.get('total_properties', 0):,}")

        st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

        # Top Locations
        if insights.get("top_locations"):
            st.markdown("### 🏙️ Top Locations by Activity")
            top_df = pd.DataFrame(insights["top_locations"])
            fig = px.bar(
                top_df,
                x="location",
                y="count",
                title="Most Active Locations",
                color="avg_price_per_m",
                color_continuous_scale="Viridis",
                labels={"count": "Number of Properties", "location": "Location"},
            )
            st.plotly_chart(fig, width='stretch')

        # Price Distribution
        if not df.empty and "price" in df.columns:
            fig = px.histogram(
                df,
                x="price",
                nbins=30,
                title="💰 Price Distribution",
                color_discrete_sequence=["#667eea"],
                labels={"price": "Price (EGP)"},
            )
            st.plotly_chart(fig, width='stretch')

        # Price per m² by Location
        if "location" in df.columns and "price_per_m" in df.columns:
            location_prices = (
                df.groupby("location")["price_per_m"]
                .mean()
                .sort_values(ascending=False)
                .head(10)
            )
            fig = px.bar(
                x=location_prices.values,
                y=location_prices.index,
                orientation="h",
                title="📍 Top 10 Most Expensive Locations (Price/m²)",
                color=location_prices.values,
                color_continuous_scale="Plasma",
                labels={"x": "Price per m² (EGP)", "y": "Location"},
            )
            st.plotly_chart(fig, width='stretch')

    else:
        # Fallback: use local calculations (from desktop file)
        st.info("Using local calculations (API insights unavailable)")

        local_insights = calculate_market_insights(df)

        if local_insights:
            col1, col2, col3 = st.columns(3)
            with col1:
                if "price_stats" in local_insights:
                    st.metric("💰 Average Price", f"{local_insights['price_stats']['mean']:,.0f} EGP")
            with col2:
                if "price_per_m_stats" in local_insights:
                    st.metric("📏 Average Price/m²", f"{local_insights['price_per_m_stats']['mean']:,.0f} EGP")
            with col3:
                if "payment_distribution" in local_insights:
                    installment_rate = local_insights["payment_distribution"].get("Installments", 0)
                    st.metric("💳 Installment Rate", f"{installment_rate:.1f}%")

            st.markdown("---")

            # Price Distribution
            if not df.empty and "price" in df.columns:
                fig = px.histogram(
                    df, x="price", text_auto=True,
                    color_discrete_sequence=["#292C60"],
                    title="Price Distribution",
                )
                st.plotly_chart(fig, width='stretch')

            # Expensive & Affordable Areas
            col4, col5 = st.columns(2)
            with col4:
                if "expensive_areas" in local_insights:
                    st.write("### 🏙️ Most Expensive Areas")
                    for area, price in local_insights["expensive_areas"].items():
                        st.write(f"**{area}:** {price:,.0f} EGP/m²")
            with col5:
                if "affordable_areas" in local_insights:
                    st.write("### 💰 Most Affordable Areas")
                    for area, price in local_insights["affordable_areas"].items():
                        st.write(f"**{area}:** {price:,.0f} EGP/m²")

        # Treemap with Buy Score (from desktop file)
        st.markdown("---")
        st.markdown("## 🗺️ Market Distribution & Buy Score Analysis")

        if not df.empty:
            with st.spinner("Calculating Buy Scores..."):
                rf_model, model_features, prop_map = train_model_once(df)
                treemap_data = create_treemap_data(df, rf_model, model_features, prop_map)

            if not treemap_data.empty:
                # Treemap
                fig_treemap = px.treemap(
                    treemap_data,
                    path=["state", "location"],
                    values="Price_Per_M_mean",
                    title="Market Distribution Tree Map مع تقييم المناطق",
                    color="Buy_Score",
                    hover_data={
                        "Price_Per_M_mean": ":.0f",
                        "Avg_Price": ":.0f",
                        "Avg_Area": ":.0f",
                        "Property_Count": True,
                        "Price_Std": ":.0f",
                    },
                    custom_data=[
                        "Price_Per_M_mean", "Avg_Price", "Avg_Area",
                        "Property_Count", "Price_Std", "Fair_Price",
                        "Buy_Score", "Buy_Label",
                        "area_score", "investment_potential",
                        "resale_liquidity", "schools_quality",
                        "Area_Intelligence_Score",
                    ],
                )

                # Enhanced hover template
                fig_treemap.update_traces(
                    hovertemplate="<b>%{label}</b><br>" +
                                 "📍 <b>المنطقه:</b> %{parent}<br>" +
                                 "-------------------<br>" +
                                 "💰 <b>متوسط سعر المتر:</b> %{customdata[0]:,.0f} EGP<br>" +
                                 "🏠 <b>متوسط السعر الكلي:</b> %{customdata[1]:,.0f} EGP<br>" +
                                 "📐 <b>متوسط المساحة:</b> %{customdata[2]:,.0f} m²<br>" +
                                 "📊 <b>عدد العقارات:</b> %{customdata[3]:,.0f}<br>" +
                                 "📈 <b>تذبذب الأسعار:</b> %{customdata[4]:,.0f} EGP<br>" +
                                 "⚖️ <b>السعر العادل:</b> %{customdata[5]:,.0f} EGP<br>" +
                                 "🏷️ <b>نقاط الشراء:</b> %{customdata[6]:.1f}/100<br>" +
                                 "📋 <b>التقييم:</b> %{customdata[7]}<br>" +
                                 "-------------------<br>" +
                                 "<b>تقييم المنطقة:</b><br>" +
                                 "• ⭐ <b>التقييم العام:</b> %{customdata[8]:.0f}/100<br>" +
                                 "• 📈 <b>الإمكانيات الاستثمارية:</b> %{customdata[9]:.0f}/5<br>" +
                                 "• 💱 <b>سيولة إعادة البيع:</b> %{customdata[10]:.0f}/5<br>" +
                                 "• 🎓 <b>جودة المدارس:</b> %{customdata[11]:.0f}/5<br>" +
                                 "<i>انقر للتكبير/التصغير</i>"
                )

                fig_treemap.update_layout(
                    margin=dict(t=50, l=25, r=25, b=20),
                    coloraxis_colorbar=dict(
                        title="Buy Score",
                        thickness=20,
                        len=0.75,
                        tickvals=[0, 25, 50, 65, 80, 100],
                        ticktext=["ضعيف", "سيء", "متوسط", "جيد", "ممتاز", "مثالي"],
                    ),
                )

                st.plotly_chart(fig_treemap, width='stretch')

                # Buy Score Gauge & Recommendations (from desktop file)
                st.markdown("---")
                st.markdown("## 🏷️ Buy Recommendation")

                col1, col2 = st.columns([1, 1])

                with col1:
                    avg_buy_score = treemap_data["Buy_Score"].mean()
                    st.plotly_chart(
                        create_buy_score_gauge(avg_buy_score),
                        width='stretch',
                    )
                    if avg_buy_score >= 80:
                        st.success("✅ فرصة شراء ممتازة في المناطق المختارة.")
                    elif avg_buy_score >= 65:
                        st.warning("🟡 خيارات جيدة متاحة – حاول التفاوض للحصول على سعر أفضل.")
                    elif avg_buy_score >= 50:
                        st.info("🟠 السوق عادل حاليًا – قارن بين الخيارات بحذر.")
                    else:
                        st.error("🔴 الأسعار مرتفعة – يُفضَّل الانتظار أو التفاوض بقوة.")

                with col2:
                    BUY_SCORE_TOOLTIP = """
                        **إزاي بنحسب Buy Score؟**

                        • 🏙️ **جودة المنطقة (25%)** - تشمل:
                        - قرب المنطقة من البحر (Near_Sea)
                        - جودة المدارس (Schools_Quality)
                        - مستوى الخدمات (Services_Level)
                        - كفاءة المواصلات (Transportation)
                        - الإمكانيات الاستثمارية (Investment_Potential)
                        - سيولة إعادة البيع (Resale_Liquidity)
                        - التقييم العام للمنطقة (Area_Score)

                        • 💰 **تنافسية السعر (30%)** - قد إيه أسعار المنطقة مناسبة مقارنة بباقي السوق.

                        • 📈 **استقرار السوق (20%)** - كل ما تذبذب الأسعار أقل، كل ما المخاطرة أقل.

                        • 🏠 **مستوى المعروض (15%)** - كل ما عدد العقارات المتاحة أكبر، فرص التفاوض بتكون أفضل.

                        • 📐 **قيمة المساحة (10%)** - المناطق ذات المساحات المتوسطة والكبيرة بتحتفظ بقيمتها.

                        • ⚖️ **تعديل السعر العادل (30% من الدرجة النهائية)** - مقارنة السعر الحالي بالسعر العادل المتوقع من النموذج.

                        **تفسير الدرجات:**
                        🟢 **80 – 100** → فرصة شراء ممتازة
                        🟡 **65 – 79** → خيار جيد
                        🟠 **50 – 64** → سعر عادل
                        🔴 **أقل من 50** → السعر مرتفع
                    """
                    st.markdown("### ℹ️ Buy Score Explanation")
                    st.info(BUY_SCORE_TOOLTIP)

                # Purchase Recommendations
                recommendations = get_purchase_recommendations(df)
                st.success(f"### ✅ توصيات الشراء:\n" + "\n".join(recommendations))

                # Property Type Distribution Charts (from desktop file)
                st.markdown("---")
                st.markdown("### 🏘️ Property Type Analysis")

                local_insights = calculate_market_insights(df)
                if "property_distribution" in local_insights:
                    prop_data = pd.DataFrame({
                        "Type": list(local_insights["property_distribution"].keys()),
                        "Percentage": list(local_insights["property_distribution"].values()),
                    })
                    fig_pie_dist = px.pie(
                        prop_data, values="Percentage", names="Type",
                        title="Property Type Market Distribution",
                    )
                    st.plotly_chart(fig_pie_dist, width='stretch')

                col7, col8 = st.columns(2)
                with col7:
                    if "property_type" in df.columns and "price" in df.columns:
                        avg_price_by_type = df.groupby("property_type")["price"].mean().reset_index()
                        fig_pie_price = px.pie(
                            avg_price_by_type, values="price", names="property_type",
                            title="Average Price by Property Type",
                        )
                        st.plotly_chart(fig_pie_price, width='stretch')
                with col8:
                    if "property_type" in df.columns and "price_per_m" in df.columns:
                        avg_pricem_by_type = df.groupby("property_type")["price_per_m"].mean().reset_index()
                        fig_pie_pm = px.pie(
                            avg_pricem_by_type, values="price_per_m", names="property_type",
                            title="Average Price/m² by Property Type",
                        )
                        st.plotly_chart(fig_pie_pm, width='stretch')

# ========== Tab 3: AI Predictions ==========
with tab3:
    st.markdown("## 🤖 AI Price Predictor")
    st.markdown("Enter property details to get an AI-powered price prediction")

    col1, col2 = st.columns(2)

    with col1:
        area_input = st.number_input(
            "📐 Area (m²)", min_value=50, max_value=1000, value=150
        )
        bedrooms_input = st.number_input(
            "🛏️ Bedrooms", min_value=1, max_value=10, value=3
        )
        bathrooms_input = st.number_input(
            "🚽 Bathrooms", min_value=1, max_value=6, value=2
        )

    with col2:
        # Get locations from data
        locations = (
            df_full["location"].unique().tolist()
            if not df_full.empty
            else ["Maadi", "Smouha", "New Cairo"]
        )
        location_input = st.selectbox("📍 Location", sorted(locations))

        property_types = (
            df_full["property_type"].unique().tolist()
            if not df_full.empty
            else ["Apartment", "Villa", "Penthouse"]
        )
        property_type_input = st.selectbox("🏘️ Property Type", property_types)

        payment_input = st.selectbox("💳 Payment Method", ["Cash", "Installments"])

    # Local ML Model Prediction (medium priority)
    st.markdown("### 🔧 Prediction Method")
    prediction_method = st.radio(
        "Choose prediction source:",
        ["🌐 API Prediction (Backend)", "🤖 Local ML Model (RandomForest)"],
        horizontal=True,
    )

    if st.button("🔮 Predict Price", width='stretch'):
        with st.spinner("Calculating prediction..."):
            if prediction_method == "🌐 API Prediction (Backend)":
                try:
                    prediction_data = {
                        "area": area_input,
                        "bedrooms": bedrooms_input,
                        "bathrooms": bathrooms_input,
                        "location": location_input,
                        "property_type": property_type_input,
                        "payment_method": payment_input,
                    }

                    response = requests.post(API_PREDICT, json=prediction_data, timeout=30)

                    if response.status_code == 200:
                        result = response.json()

                        st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

                        col1, col2 = st.columns(2)

                        with col1:
                            st.markdown(
                                f"""
                            <div class="success-box">
                                <h3>🎯 Predicted Price</h3>
                                <h2>{result['predicted_price']:,.0f} EGP</h2>
                                <p>💰 {result['predicted_price_per_m']:,.0f} EGP/m²</p>
                            </div>
                            """,
                                unsafe_allow_html=True,
                            )

                        with col2:
                            st.markdown(
                                f"""
                            <div class="metric-card">
                                <h3>📊 Confidence Interval</h3>
                                <p>Lower: {result['confidence_lower']:,.0f} EGP</p>
                                <p>Upper: {result['confidence_upper']:,.0f} EGP</p>
                                <p>🎯 Area Score: {result['area_intelligence_score']}/100</p>
                            </div>
                            """,
                                unsafe_allow_html=True,
                            )

                        st.markdown(
                            f"""
                        <div class="warning-box">
                            <h3>💡 Recommendation</h3>
                            <p>{result['recommendation']}</p>
                        </div>
                        """,
                            unsafe_allow_html=True,
                        )
                    else:
                        st.error("Failed to get prediction. Please try again.")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

            else:  # Local ML Model
                try:
                    # Train model on full data
                    rf_model, model_features, prop_map = train_model_once(df_full)

                    if rf_model is None:
                        st.error("⚠️ Local model not available. Need at least 50 properties for training. Try API prediction instead.")
                    else:
                        # Prepare input
                        input_data = {
                            "area": area_input,
                            "bedrooms": bedrooms_input,
                            "bathrooms": bathrooms_input,
                            "price_per_m": 0,
                            "payment_code": 0 if payment_input == "Cash" else 1,
                            "property_type_code": prop_map.get(property_type_input, 0),
                            "near_sea": 0,
                            "schools_quality": 3,
                            "services_level": 3,
                            "transportation": 3,
                            "investment_potential": 3,
                            "resale_liquidity": 3,
                            "area_score": 70,
                        }

                        pred_vector = [input_data.get(f, 0) for f in model_features]
                        predicted_price = rf_model.predict([pred_vector])[0]
                        predicted_price_per_m = predicted_price / area_input if area_input > 0 else 0

                        st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

                        col1, col2 = st.columns(2)

                        with col1:
                            st.markdown(
                                f"""
                            <div class="success-box">
                                <h3>🎯 Predicted Price (Local ML)</h3>
                                <h2>{predicted_price:,.0f} EGP</h2>
                                <p>💰 {predicted_price_per_m:,.0f} EGP/m²</p>
                            </div>
                            """,
                                unsafe_allow_html=True,
                            )

                        with col2:
                            mae = st.session_state.get("model_mae", 0)
                            st.markdown(
                                f"""
                            <div class="metric-card">
                                <h3>📊 Model Accuracy</h3>
                                <p>📉 Mean Absolute Error: {mae:,.0f} EGP</p>
                                <p>🎯 Features Used: {len(model_features)}</p>
                                <p>📚 Training Data: {len(df_full)} properties</p>
                            </div>
                            """,
                                unsafe_allow_html=True,
                            )

                        # Simple recommendation
                        st.markdown(
                            f"""
                        <div class="warning-box">
                            <h3>💡 Recommendation</h3>
                            <p>Based on local ML model analysis, the predicted price for a {property_type_input.lower()} in {location_input} with {bedrooms_input} bedrooms is approximately {predicted_price:,.0f} EGP.</p>
                        </div>
                        """,
                            unsafe_allow_html=True,
                        )

                except Exception as e:
                    st.error(f"Local ML Error: {str(e)}")

# ========== Tab 4: Time Analysis ==========
with tab4:
    st.markdown("## ⏰ Time-Based Analysis")
    st.markdown("Analyze property trends over time")

    # Check if we have date-related columns
    date_columns = [col for col in df_full.columns if 'date' in col.lower() or 'time' in col.lower() or 'created' in col.lower() or 'updated' in col.lower()]

    if date_columns:
        st.success(f"Found date columns: {', '.join(date_columns)}")
        date_col = st.selectbox("Select date column for analysis:", date_columns)

        if not df_full.empty and date_col in df_full.columns:
            df_time = df_full.copy()
            df_time[date_col] = pd.to_datetime(df_time[date_col], errors='coerce')
            df_time = df_time.dropna(subset=[date_col])

            if not df_time.empty:
                # Time range selector
                min_date = df_time[date_col].min()
                max_date = df_time[date_col].max()

                st.markdown(f"**Data range:** {min_date.date()} to {max_date.date()}")

                date_range = st.date_input(
                    "Select date range:",
                    value=(min_date.date(), max_date.date()),
                    min_value=min_date.date(),
                    max_value=max_date.date(),
                )

                if len(date_range) == 2:
                    start_date, end_date = date_range
                    mask = (df_time[date_col].dt.date >= start_date) & (df_time[date_col].dt.date <= end_date)
                    df_time_filtered = df_time[mask]

                    if not df_time_filtered.empty:
                        # Time aggregation
                        agg_period = st.selectbox(
                            "Aggregate by:",
                            ["Day", "Week", "Month", "Quarter", "Year"],
                            index=2,
                        )

                        if agg_period == "Day":
                            df_time_filtered["period"] = df_time_filtered[date_col].dt.date
                        elif agg_period == "Week":
                            df_time_filtered["period"] = df_time_filtered[date_col].dt.isocalendar().week.astype(str) + "-" + df_time_filtered[date_col].dt.isocalendar().year.astype(str)
                        elif agg_period == "Month":
                            df_time_filtered["period"] = df_time_filtered[date_col].dt.to_period("M").astype(str)
                        elif agg_period == "Quarter":
                            df_time_filtered["period"] = df_time_filtered[date_col].dt.to_period("Q").astype(str)
                        else:
                            df_time_filtered["period"] = df_time_filtered[date_col].dt.year.astype(str)

                        st.markdown("---")
                        st.markdown(f"### 📊 Trends Over Time ({agg_period}ly)")

                        col1, col2 = st.columns(2)

                        with col1:
                            # Properties over time
                            props_over_time = df_time_filtered.groupby("period").size().reset_index(name="count")
                            fig_time1 = px.line(
                                props_over_time, x="period", y="count",
                                title=f"📈 Number of Properties Over Time ({agg_period}ly)",
                                markers=True,
                                labels={"period": "Period", "count": "Property Count"},
                            )
                            fig_time1.update_layout(height=400)
                            st.plotly_chart(fig_time1, width='stretch')

                        with col2:
                            # Average price over time
                            if "price" in df_time_filtered.columns:
                                price_over_time = df_time_filtered.groupby("period")["price"].mean().reset_index()
                                fig_time2 = px.line(
                                    price_over_time, x="period", y="price",
                                    title=f"💰 Average Price Over Time ({agg_period}ly)",
                                    markers=True,
                                    labels={"period": "Period", "price": "Avg Price (EGP)"},
                                )
                                fig_time2.update_layout(height=400)
                                st.plotly_chart(fig_time2, width='stretch')

                        # Price per m² over time
                        if "price_per_m" in df_time_filtered.columns:
                            ppm_over_time = df_time_filtered.groupby("period")["price_per_m"].mean().reset_index()
                            fig_time3 = px.line(
                                ppm_over_time, x="period", y="price_per_m",
                                title=f"📏 Average Price/m² Over Time ({agg_period}ly)",
                                markers=True,
                                labels={"period": "Period", "price_per_m": "Avg Price/m² (EGP)"},
                            )
                            fig_time3.update_layout(height=400)
                            st.plotly_chart(fig_time3, width='stretch')

                        # Property type distribution over time
                        if "property_type" in df_time_filtered.columns:
                            st.markdown("### 🏘️ Property Type Distribution Over Time")
                            type_time = df_time_filtered.groupby(["period", "property_type"]).size().reset_index(name="count")
                            fig_time4 = px.area(
                                type_time, x="period", y="count", color="property_type",
                                title=f"Property Type Distribution Over Time ({agg_period}ly)",
                                labels={"period": "Period", "count": "Count", "property_type": "Type"},
                            )
                            fig_time4.update_layout(height=500)
                            st.plotly_chart(fig_time4, width='stretch')

                        # Payment method trends
                        if "payment_method" in df_time_filtered.columns:
                            st.markdown("### 💳 Payment Method Trends")
                            payment_time = df_time_filtered.groupby(["period", "payment_method"]).size().reset_index(name="count")
                            fig_time5 = px.bar(
                                payment_time, x="period", y="count", color="payment_method",
                                title=f"Payment Method Over Time ({agg_period}ly)",
                                barmode="group",
                                labels={"period": "Period", "count": "Count", "payment_method": "Payment"},
                            )
                            fig_time5.update_layout(height=400)
                            st.plotly_chart(fig_time5, width='stretch')

                        # Summary metrics
                        st.markdown("---")
                        st.markdown("### 📊 Time Period Summary")

                        period_summary = df_time_filtered.groupby("period").agg({
                            "price": ["mean", "min", "max", "count"],
                            "area": "mean",
                            "price_per_m": "mean",
                        }).round(0)

                        period_summary.columns = ["Avg Price", "Min Price", "Max Price", "Count", "Avg Area", "Avg Price/m²"]
                        st.dataframe(period_summary, width='stretch')

                    else:
                        st.info("No data in selected date range.")
                else:
                    st.info("Please select both start and end dates.")
            else:
                st.warning("No valid date data after parsing.")
        else:
            st.warning("Selected date column not found in data.")
    else:
        st.info("⏰ No date columns found in the current data. Time analysis requires date/time data in the property records.")

        # Show what columns are available
        st.markdown("### Available Columns:")
        st.write(", ".join(df_full.columns.tolist()) if not df_full.empty else "No data loaded")

        # Provide a simulated time analysis using property ID as proxy
        st.markdown("---")
        st.markdown("### 📈 Simulated Trend Analysis")
        st.markdown("Since no date data is available, here's a trend analysis based on property ordering:")

        if not df.empty and len(df) > 10:
            df_sim = df.copy()
            df_sim["simulated_index"] = range(len(df_sim))

            col1, col2 = st.columns(2)
            with col1:
                # Price trend by index
                fig_sim1 = px.line(
                    df_sim, x="simulated_index", y="price" if "price" in df_sim.columns else None,
                    title="📈 Price Trend (by entry order)",
                    labels={"simulated_index": "Property #", "price": "Price (EGP)"},
                )
                fig_sim1.update_layout(height=400)
                st.plotly_chart(fig_sim1, width='stretch')

            with col2:
                if "price_per_m" in df_sim.columns:
                    fig_sim2 = px.line(
                        df_sim, x="simulated_index", y="price_per_m",
                        title="📏 Price/m² Trend (by entry order)",
                        labels={"simulated_index": "Property #", "price_per_m": "Price/m² (EGP)"},
                    )
                    fig_sim2.update_layout(height=400)
                    st.plotly_chart(fig_sim2, width='stretch')

            st.markdown("""
            > 💡 **Tip:** To get full time analysis, add a `created_at` or `scraped_date` column to your property data. 
            > The backend can be updated to track when each property was scraped/added.
            """)

# ========== Property Comparison Tool (medium priority) ==========
st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
with st.expander("🔍 Property Comparison Tool", expanded=False):
    st.markdown("### 🔍 Compare Properties Side by Side")

    if not df_full.empty and len(df_full) > 1:
        # Select properties to compare
        property_options = df_full.apply(
            lambda row: f"{row.get('title', 'Unknown')} - {row.get('location', '')} - {row.get('price', 0):,.0f} EGP",
            axis=1
        ).tolist()

        selected_indices = st.multiselect(
            "Select 2-4 properties to compare:",
            options=range(len(property_options)),
            format_func=lambda i: property_options[i] if i < len(property_options) else "",
            max_selections=4,
        )

        if len(selected_indices) >= 2:
            compare_df = df_full.iloc[selected_indices]

            # Comparison columns
            compare_cols = [
                "title", "property_type", "price", "price_per_m",
                "area", "bedrooms", "bathrooms", "location",
                "state", "payment_method",
            ]
            available_compare_cols = [c for c in compare_cols if c in compare_df.columns]

            st.markdown("### 📊 Comparison Table")
            # Transpose for better comparison
            comparison_table = compare_df[available_compare_cols].T
            comparison_table.columns = [f"Property {i+1}" for i in range(len(selected_indices))]
            st.dataframe(comparison_table, width='stretch')

            # Visual comparison
            st.markdown("### 📈 Visual Comparison")
            col1, col2 = st.columns(2)

            with col1:
                if "price" in compare_df.columns:
                    fig_comp1 = px.bar(
                        compare_df, x=compare_df.index, y="price",
                        title="💰 Price Comparison",
                        color="property_type" if "property_type" in compare_df.columns else None,
                        text_auto=".0f",
                        labels={"index": "Property", "price": "Price (EGP)"},
                    )
                    fig_comp1.update_layout(height=400)
                    st.plotly_chart(fig_comp1, width='stretch')

            with col2:
                if "price_per_m" in compare_df.columns:
                    fig_comp2 = px.bar(
                        compare_df, x=compare_df.index, y="price_per_m",
                        title="📏 Price/m² Comparison",
                        color="property_type" if "property_type" in compare_df.columns else None,
                        text_auto=".0f",
                        labels={"index": "Property", "price_per_m": "Price/m² (EGP)"},
                    )
                    fig_comp2.update_layout(height=400)
                    st.plotly_chart(fig_comp2, width='stretch')

            # Radar chart for comparison
            st.markdown("### 🕸️ Property Features Radar")
            radar_metrics = ["price", "area", "bedrooms", "bathrooms", "price_per_m"]
            available_radar = [m for m in radar_metrics if m in compare_df.columns]

            if len(available_radar) >= 3:
                radar_data = compare_df[available_radar].copy()
                # Normalize for radar
                for col in radar_data.columns:
                    if radar_data[col].max() != radar_data[col].min():
                        radar_data[col] = (radar_data[col] - radar_data[col].min()) / (radar_data[col].max() - radar_data[col].min())
                    else:
                        radar_data[col] = 0.5

                fig_radar = go.Figure()
                for i, idx in enumerate(radar_data.index):
                    fig_radar.add_trace(go.Scatterpolar(
                        r=radar_data.loc[idx].tolist() + [radar_data.loc[idx].tolist()[0]],
                        theta=available_radar + [available_radar[0]],
                        fill='toself',
                        name=f"Property {i+1}",
                    ))

                fig_radar.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
                    title="Property Features Comparison (Normalized)",
                    height=500,
                )
                st.plotly_chart(fig_radar, width='stretch')
        else:
            st.info("Select at least 2 properties to compare.")
    else:
        st.info("Not enough properties loaded for comparison.")

# Footer
st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
st.markdown(
    f"""
    <div style="text-align: center; padding: 20px; color: #666;">
        <p>🏠 Real Estate Egypt Dashboard | Powered by AI</p>
        <p style="font-size: 0.8em;">Data updated in real-time from API | Version 3.0 - Merged Edition</p>
    </div>
    """,
    unsafe_allow_html=True,
)
