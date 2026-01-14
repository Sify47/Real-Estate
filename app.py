import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
import requests
from io import StringIO
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error

# إعداد الصفحة
st.set_page_config(page_title="Real Estate Egypt", page_icon="🏠", layout="wide")

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
</style>
""",
    unsafe_allow_html=True,
)


# --- 1. تحميل البيانات ---
@st.cache_data(ttl=300)
def load_data():
    try:
        try:
            github_username = "Sify47"
            github_repo = "Real-Estate"
            github_raw_url = f"https://raw.githubusercontent.com/{github_username}/{github_repo}/main/Final1.csv"
            response = requests.get(github_raw_url, timeout=10)
            if response.status_code == 200:
                df = pd.read_csv(StringIO(response.text))
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
        if os.path.exists("Final1.csv") and os.path.getsize("Final1.csv") > 0:
            df = pd.read_csv("Final1.csv")
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
        # Dummy Data Fallback
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


# --- 2. تدريب النموذج (مرة واحدة فقط) ---
@st.cache_resource
def train_model_once(df):
    """
    تدريب النموذج مرة واحدة وحفظه في الذاكرة لتسريع التطبيق.
    """
    ml_df = df.copy()

    # Preprocessing
    if "Payment_Method" in ml_df.columns:
        ml_df["Payment_Code"] = (
            ml_df["Payment_Method"]
            .map({"Cash": 0, "Installments": 1, "نقدي": 0, "تقسيط": 1})
            .fillna(0)
        )

    property_map = {}
    if "PropertyType" in ml_df.columns:
        property_types = ml_df["PropertyType"].unique()
        property_map = {pt: i for i, pt in enumerate(property_types)}
        ml_df["PropertyType_Code"] = ml_df["PropertyType"].map(property_map)

    # تحديد الميزات
    numeric_features = []
    candidates = [
        "Area",
        "Bedrooms",
        "Bathrooms",
        "Price_Per_M",
        "Down_Payment",
        "Payment_Code",
        "PropertyType_Code",
    ]
    for col in candidates:
        if col in ml_df.columns:
            numeric_features.append(col)

    ml_df = ml_df[numeric_features + ["Price"]].dropna()

    if len(ml_df) < 50:
        return None, [], {}

    X = ml_df[numeric_features]
    y = ml_df["Price"]

    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=45
        )

        # زيادة الدقة قليلاً لأن التدريب يحصل مرة واحدة
        rf_model = RandomForestRegressor(
            n_estimators=150, max_depth=20, random_state=47, n_jobs=-1
        )
        rf_model.fit(X_train, y_train)

        # حساب مقاييس الأداء للعرض (اختياري)
        y_pred = rf_model.predict(X_test)
        mae = mean_absolute_error(y_test, y_pred)
        # يمكن حفظ mae في session_state إذا أردت عرضه

        return rf_model, numeric_features, property_map
    except Exception as e:
        print(f"ML Training Error: {e}")
        return None, [], {}


def calculate_market_insights(df):
    insights = {}
    if len(df) == 0:
        return insights
    if "Price" in df.columns:
        insights["price_stats"] = {
            "mean": df["Price"].mean(),
            "median": df["Price"].median(),
            "min": df["Price"].min(),
            "max": df["Price"].max(),
        }
    if "Price_Per_M" in df.columns:
        insights["price_per_m_stats"] = {
            "mean": df["Price_Per_M"].mean(),
            "median": df["Price_Per_M"].median(),
        }
    if "Location" in df.columns and "Price_Per_M" in df.columns:
        location_prices = (
            df.groupby("Location")["Price_Per_M"].mean().sort_values(ascending=False)
        )
        insights["expensive_areas"] = location_prices.head(5).to_dict()
        insights["affordable_areas"] = location_prices.tail(5).to_dict()
    if "PropertyType" in df.columns:
        property_dist = df["PropertyType"].value_counts(normalize=True) * 100
        insights["property_distribution"] = property_dist.to_dict()
    if "Payment_Method" in df.columns:
        payment_dist = df["Payment_Method"].value_counts(normalize=True) * 100
        insights["payment_distribution"] = payment_dist.to_dict()
    return insights


# --- 3. دالة Treemap المعدلة (تستخدم النموذج الجاهز) ---
def create_treemap_data(filtered_df, model, features, prop_map):
    # Aggregations
    avg_price1 = (
        filtered_df.groupby(["State", "Location"])["Price_Per_M"].mean().reset_index()
    )
    stats_df = (
        filtered_df.groupby(["State", "Location"])
        .agg({"Price_Per_M": ["mean", "count", "std"], "Price": "mean", "Area": "mean"})
        .reset_index()
    )
    stats_df.columns = [
        "_".join(col).strip("_") if col[1] else col[0]
        for col in stats_df.columns.values
    ]

    avg_price1 = avg_price1.merge(
        stats_df[
            [
                "State",
                "Location",
                "Price_Per_M_count",
                "Price_Per_M_std",
                "Price_mean",
                "Area_mean",
            ]
        ],
        on=["State", "Location"],
        how="left",
    )

    avg_price1 = avg_price1.rename(
        columns={
            "Price_Per_M": "Price_Per_M_mean",
            "Price_mean": "Avg_Price",
            "Area_mean": "Avg_Area",
            "Price_Per_M_count": "Property_Count",
            "Price_Per_M_std": "Price_Std",  # Note: Adjusted name mapping
        }
    )

    # Fix renaming if needed
    if "Price_Per_M_std" in avg_price1.columns:
        avg_price1.rename(columns={"Price_Per_M_std": "Price_Std"}, inplace=True)

    # Fill NaN Std with 0 for single properties
    avg_price1["Price_Std"] = avg_price1["Price_Std"].fillna(0)

    # --- Prediction Logic using Cached Model ---
    if model is not None and features:
        try:
            # Prepare batch input for efficiency could be better, but iterrows is fine for small location counts
            for idx, row in avg_price1.iterrows():
                # Create input vector matching training features
                input_data = {
                    "Area": row["Avg_Area"],
                    "Bedrooms": 3,  # Assumption
                    "Bathrooms": 2,  # Assumption
                    "Price_Per_M": row["Price_Per_M_mean"],
                    "Down_Payment": 0,
                    "Payment_Code": 0,  # Cash assumption
                    "PropertyType_Code": prop_map.get(
                        "Apartment", 0
                    ),  # Default type assumption
                }

                # Align columns
                pred_vector = []
                for f in features:
                    pred_vector.append(input_data.get(f, 0))

                # Predict
                predicted_price = model.predict([pred_vector])[0]
                avg_price1.at[idx, "Fair_Price"] = predicted_price
        except Exception as e:
            # Fallback
            avg_price1["Fair_Price"] = (
                avg_price1["Price_Per_M_mean"] * avg_price1["Avg_Area"]
            )
    else:
        # Fallback if no model
        avg_price1["Fair_Price"] = (
            avg_price1["Price_Per_M_mean"] * avg_price1["Avg_Area"]
        )

    # --- Scoring Logic ---
    price_min = avg_price1["Price_Per_M_mean"].min()
    price_max = avg_price1["Price_Per_M_mean"].max()

    # Avoid division by zero
    if price_max == price_min:
        avg_price1["Price_Score"] = 0.5
    else:
        avg_price1["Price_Score"] = 1 - (
            (avg_price1["Price_Per_M_mean"] - price_min) / (price_max - price_min)
        )

    std_min = avg_price1["Price_Std"].min()
    std_max = avg_price1["Price_Std"].max()

    if std_max == std_min:
        avg_price1["Stability_Score"] = 0.5
    else:
        avg_price1["Stability_Score"] = 1 - (
            (avg_price1["Price_Std"] - std_min) / (std_max - std_min)
        )

    count_min = avg_price1["Property_Count"].min()
    count_max = avg_price1["Property_Count"].max()
    area_min = avg_price1["Avg_Area"].min()
    area_max = avg_price1["Avg_Area"].max()

    avg_price1["Area_Score"] = (
        (avg_price1["Avg_Area"] - area_min) / (area_max - area_min)
        if area_max != area_min
        else 0.5
    )
    avg_price1["Supply_Score"] = (
        (avg_price1["Property_Count"] - count_min) / (count_max - count_min)
        if count_max != count_min
        else 0.5
    )

    # Buy Score Calculation
    avg_price1["Buy_Score"] = (
        avg_price1["Price_Score"] * 0.40
        + avg_price1["Stability_Score"] * 0.25
        + avg_price1["Supply_Score"] * 0.20
        + avg_price1["Area_Score"] * 0.15
    ) * 100

    avg_price1["Buy_Score"] = avg_price1["Buy_Score"].clip(0, 100)

    # Value Score adjustment
    if "Fair_Price" in avg_price1.columns:
        avg_price1["Value_Score"] = avg_price1.apply(
            lambda row: (
                100 * (1 - (row["Avg_Price"] / row["Fair_Price"]))
                if row["Fair_Price"] > 0
                else 50
            ),
            axis=1,
        ).clip(0, 100)

        avg_price1["Buy_Score"] = (
            avg_price1["Buy_Score"] * 0.7 + avg_price1["Value_Score"] * 0.3
        )

    def buy_label(score):
        if score >= 80:
            return " فرصة شراء ممتازة 🟢"
        elif score >= 65:
            return "خيار جيد 🟡"
        elif score >= 50:
            return "كويس 🟠"
        else:
            return "سعر عالى 🔴"

    avg_price1["Buy_Label"] = avg_price1["Buy_Score"].apply(buy_label)

    avg_price1["Recommendation"] = avg_price1.apply(
        lambda row: (
            "🏆 Highly Recommended"
            if row["Buy_Score"] >= 80
            else (
                "👍 Good Value"
                if row["Buy_Score"] >= 65
                else "🤔 Consider" if row["Buy_Score"] >= 50 else "⚠️ Overpriced"
            )
        ),
        axis=1,
    )

    return avg_price1


def get_purchase_recommendations(filtered_df):
    recommendations = []
    try:
        if not filtered_df.empty and "Bedrooms" in filtered_df.columns:
            room_counts = filtered_df["Bedrooms"].value_counts()
            if not room_counts.empty:
                most_popular = room_counts.idxmax()
                recommendations.append(
                    f"- الشقق {most_popular} غرف هي الأكثر طلبًا حاليًا"
                )
    except:
        recommendations.append("- الشقق 3-4 غرف هي الأكثر طلبًا بشكل عام")
    recommendations.append(
        "- لو ميزانيتك متوسطة → ركّز على المناطق ذات سعر متر أقل من المتوسط العام"
    )
    recommendations.append(
        "- تجنّب المناطق ذات الانحراف السعري العالي (عدم استقرار الأسعار)"
    )
    recommendations.append("- Fair Price هي مؤشر جيد لتقييم السعر العادل للعقار")
    recommendations.append(
        "- Buy Score يساعدك في اختيار المناطق ذات الفرص الأفضل للشراء"
    )
    return recommendations


def calculate_area_insights(filtered_df):
    if (
        filtered_df.empty
        or "Area" not in filtered_df.columns
        or "Price" not in filtered_df.columns
    ):
        return "120 و 180 متر", "بمعدل أسرع"
    try:
        area_counts, area_bins = np.histogram(filtered_df["Area"].dropna(), bins=10)
        max_density_idx = np.argmax(area_counts)
        best_area_min = area_bins[max_density_idx]
        best_area_max = area_bins[max_density_idx + 1]
        best_area_text = f"{int(best_area_min)} و {int(best_area_max)} متر"
    except:
        best_area_text = "120 و 180 متر"
    try:
        median_area = filtered_df["Area"].median()
        small_apartments = filtered_df[filtered_df["Area"] <= median_area]
        large_apartments = filtered_df[filtered_df["Area"] > median_area]
        if not small_apartments.empty and not large_apartments.empty:
            small_price_per_m = (
                small_apartments["Price"].mean() / small_apartments["Area"].mean()
            )
            large_price_per_m = (
                large_apartments["Price"].mean() / large_apartments["Area"].mean()
            )
            price_increase_rate = (
                (large_price_per_m - small_price_per_m) / small_price_per_m
            ) * 100
            if price_increase_rate > 0:
                price_rate_text = f"{price_increase_rate:.1f}%"
            else:
                price_rate_text = "بمعدل أسرع"
        else:
            price_rate_text = "بمعدل أسرع"
    except:
        price_rate_text = "بمعدل أسرع"
    return best_area_text, price_rate_text


# --- Main Execution ---
df = load_data()

# 4. تفعيل تدريب النموذج فور تحميل البيانات
# هذا السطر يعمل مرة واحدة عند تشغيل السيرفر أو تحميل الكاش
rf_model, model_features, prop_map = train_model_once(df)

if "last_update" not in st.session_state:
    st.session_state["last_update"] = "Unknown"

st.markdown(
    '<h1 class="main-title">🏠 Real Estate Dashboard</h1>',
    unsafe_allow_html=True,
)

tab1, tab2 = st.tabs(["📊 Dashboard", "📈 Market Insights"])
view = ["Sea", "Club", "Street"]

with tab1:
    st.sidebar.header("🔍 Filters")
    property_types = (
        ["All"] + sorted(df["PropertyType"].dropna().unique().tolist())
        if "PropertyType" in df.columns
        else ["All"]
    )
    selected_type = st.sidebar.selectbox("Property Type", property_types)
    bed_types = (
        ["All"] + sorted(df["Bedrooms"].dropna().unique().tolist())
        if "Bedrooms" in df.columns
        else ["All"]
    )
    bed_types = st.sidebar.selectbox("Bedrooms", bed_types)
    Bathrooms_types = (
        ["All"] + sorted(df["Bathrooms"].dropna().unique().tolist())
        if "Bathrooms" in df.columns
        else ["All"]
    )
    Bathrooms_types = st.sidebar.selectbox("Bathrooms", Bathrooms_types)
    view_types = ["All"] + sorted(view) if "Title" in df.columns else ["All"]
    selected_view = st.sidebar.selectbox("View", view_types)
    cities = (
        ["All"] + sorted(df["State"].dropna().unique().tolist())
        if "State" in df.columns
        else ["All"]
    )
    selected_city = st.sidebar.selectbox("State", cities)
    locations = (
        ["All"] + sorted(df["Location"].dropna().unique().tolist())
        if "Location" in df.columns
        else ["All"]
    )
    selected_location = st.sidebar.selectbox("Location", locations)
    if "Price" in df.columns:
        price_min = int(df["Price"].min())
        price_max = int(df["Price"].max())

        price_min_simplified = price_min // 1000000
        price_max_simplified = price_max // 1000000

        price_range_simple = st.sidebar.slider(
            "Price Range (Million EGP)",
            price_min_simplified,
            price_max_simplified,
            (price_min_simplified, price_max_simplified),
        )

        price_range = (price_range_simple[0] * 1000000, price_range_simple[1] * 1000000)
    if "Area" in df.columns:
        area_min = int(df["Area"].min())
        area_max = int(df["Area"].max())
        area_range = st.sidebar.slider(
            "Area Range (m²)", area_min, area_max, (area_min, area_max)
        )
    payment_methods = (
        ["All"] + sorted(df["Payment_Method"].dropna().unique().tolist())
        if "Payment_Method" in df.columns
        else ["All"]
    )
    selected_payment = st.sidebar.selectbox("Payment Method", payment_methods)

    filtered_df = df.copy()
    if selected_city != "All" and "State" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["State"] == selected_city]
    if bed_types != "All" and "Bedrooms" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["Bedrooms"] == bed_types]
    if Bathrooms_types != "All" and "Bathrooms" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["Bathrooms"] == Bathrooms_types]
    if selected_type != "All" and "PropertyType" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["PropertyType"] == selected_type]
    if selected_view != "All" and "Title" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["Title"]
            .astype(str)
            .str.contains(selected_view, case=False, na=False)
        ]
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

    st.markdown(
        "💡 **معلومة مهمة:** متوسط السعر والمساحة بيعكسوا اختياراتك الحالية. غيّر الفلاتر وشوف إزاي القرار بيتغير."
    )

    # 5. تمرير النموذج المدرب للدالة
    treemap_data = create_treemap_data(filtered_df, rf_model, model_features, prop_map)

    # Check if empty to avoid errors
    if not treemap_data.empty:
        if treemap_data["Buy_Label"].value_counts().idxmax() == "سعر عالى 🔴":
            st.markdown(
                '<div class="metric-card" style="background: linear-gradient(135deg, #ff4e50 0%, #f9d423 100%);">السوق عالى السعر حاليًا، خليك حذر في اختياراتك!</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="metric-card" style="background: linear-gradient(135deg, #43cea2 0%, #185a9d 100%);">السوق مناسب للشراء حاليًا، استغل الفرص!</div>',
                unsafe_allow_html=True,
            )

    st.subheader("📈 Analytics")

    if not filtered_df.empty:
        if "State" in filtered_df.columns:
            fig1 = px.bar(
                filtered_df["State"].value_counts().reset_index().head(20),
                x="State",
                y="count",
                title="Properties Distribution by State (Top 20)",
                color="count",
                color_continuous_scale="Viridis",
            )
            st.plotly_chart(fig1, use_container_width=True)

        fig7 = px.violin(
            filtered_df,
            "PropertyType",
            "Price",
            box=True,
            color="Payment_Method",
            title="Price Distribution by Property Type",
        )
        st.plotly_chart(fig7, use_container_width=True)

        fig14 = px.violin(
            filtered_df,
            x="Payment_Method",
            y="Price",
            box=True,
            points="all",
            color="Payment_Method",
            title="Price Distribution by Payment Method",
        )
        st.plotly_chart(fig14, use_container_width=True)

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

        best_area_text, price_rate_text = calculate_area_insights(filtered_df)
        st.markdown(
            f"**💡 ملاحظة مهمة:** أفضل قيمة مقابل السعر غالبًا بين **{best_area_text}**. المساحات الأكبر سعرها بيزيد **{price_rate_text}** من قيمتها الفعلية."
        )

        if "Location" in filtered_df.columns and "Price_Per_M" in filtered_df.columns:
            st.markdown(
                "📍 **مقارنة المناطق** مش دايمًا المنطقة الأغلى هي الأفضل. في مناطق سعر المتر أقل لكن الطلب عليها أعلى، وده بيدي قيمة أفضل مقابل السعر."
            )
            col1, col2 = st.columns(2)
            with col1:
                avg_price_by_location = (
                    filtered_df.groupby("Location")
                    .agg({"Price_Per_M": "mean"})
                    .reset_index()
                )
                fig3 = px.bar(
                    avg_price_by_location.sort_values(
                        "Price_Per_M", ascending=True
                    ).head(10),
                    x="Location",
                    y="Price_Per_M",
                    title="Average Price Per m² by Location (Top 10) 'ASC'",
                    color="Price_Per_M",
                    color_continuous_scale="Plasma",
                )
                st.plotly_chart(fig3, use_container_width=True)
            with col2:
                avg_price_by_location_desc = (
                    filtered_df.groupby("Location")
                    .agg({"Price_Per_M": "mean"})
                    .reset_index()
                )
                fig4 = px.bar(
                    avg_price_by_location_desc.sort_values(
                        "Price_Per_M", ascending=False
                    ).head(10),
                    x="Location",
                    y="Price_Per_M",
                    title="Average Price Per m² by Location (Top 10) 'DESC'",
                    color="Price_Per_M",
                    color_continuous_scale="Plasma",
                )
                st.plotly_chart(fig4, use_container_width=True)

        if "State" in filtered_df.columns and "Price_Per_M" in filtered_df.columns:
            col1, col2 = st.columns(2)
            with col1:
                avg_price_by_state = (
                    filtered_df.groupby("State")
                    .agg({"Price_Per_M": "mean"})
                    .reset_index()
                )
                fig5 = px.bar(
                    avg_price_by_state.sort_values("Price_Per_M", ascending=False).head(
                        10
                    ),
                    x="State",
                    y="Price_Per_M",
                    title="Average Price Per m² by State (Top 10) 'DESC'",
                    color="Price_Per_M",
                    color_continuous_scale="Plasma",
                )
                st.plotly_chart(fig5, use_container_width=True)
            with col2:
                fig6 = px.bar(
                    avg_price_by_state.sort_values("Price_Per_M", ascending=True).head(
                        10
                    ),
                    x="State",
                    y="Price_Per_M",
                    title="Average Price Per m² by State (Top 10) 'ASC'",
                    color="Price_Per_M",
                    color_continuous_scale="Plasma",
                )
                st.plotly_chart(fig6, use_container_width=True)
    fig12 = px.box(
        filtered_df,
        x="Bedrooms",
        y="Price_Per_M",
        color="PropertyType",
        title="Price per m² Distribution by Bedrooms Count",
    )
    st.plotly_chart(fig12, use_container_width=True)

    fig13 = px.box(
        filtered_df,
        x="Bathrooms",
        y="Price_Per_M",
        color="PropertyType",
        title="Price per m² Distribution by Bathrooms Count",
    )
    st.plotly_chart(fig13, use_container_width=True)

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
            "Title",
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

with tab2:
    st.subheader("📈 Market Insights & Analytics")
    insights = calculate_market_insights(df)
    if insights:
        col1, col2, col3 = st.columns(3)
        with col1:
            if "price_stats" in insights:
                st.metric(
                    "💰 Average Price", f"{insights['price_stats']['mean']:,.0f} EGP"
                )
        with col2:
            if "price_per_m_stats" in insights:
                st.metric(
                    "📏 Average Price/m²",
                    f"{insights['price_per_m_stats']['mean']:,.0f} EGP",
                )
        with col3:
            if "payment_distribution" in insights:
                installment_rate = insights["payment_distribution"].get(
                    "Installments", 0
                )
                st.metric("💳 Installment Rate", f"{installment_rate:.1f}%")

        st.markdown("---")

        f = px.histogram(
            filtered_df,
            "Price",
            text_auto=True,
            color_discrete_sequence=["#292C60"],
            title="Price Distribution",
        )
        st.plotly_chart(f, use_container_width=True)

        col4, col5 = st.columns(2)
        with col4:
            if "expensive_areas" in insights:
                st.write("### 🏙️ Most Expensive Areas")
                for area, price in insights["expensive_areas"].items():
                    st.write(f"**{area}:** {price:,.0f} EGP/m²")
        with col5:
            if "affordable_areas" in insights:
                st.write("### 💰 Most Affordable Areas")
                for area, price in insights["affordable_areas"].items():
                    st.write(f"**{area}:** {price:,.0f} EGP/m²")

        if not filtered_df.empty:
            # 6. تمرير النموذج المدرب للدالة هنا أيضاً
            treemap_data = create_treemap_data(
                filtered_df, rf_model, model_features, prop_map
            )

            fig15 = px.treemap(
                treemap_data,
                path=["State", "Location"],
                values="Price_Per_M_mean",
                title="Market Distribution Tree Map",
                color="Buy_Score",
                hover_data={
                    "Price_Per_M_mean": ":.0f",
                    "Avg_Price": ":.0f",
                    "Avg_Area": ":.0f",
                    "Property_Count": True,
                    "Price_Std": ":.0f",
                },
                custom_data=[
                    "Price_Per_M_mean",
                    "Avg_Price",
                    "Avg_Area",
                    "Property_Count",
                    "Price_Std",
                    "Fair_Price",
                    "Buy_Score",
                    "Buy_Label",
                ],
            )
            fig15.update_traces(
                hovertemplate="<b>%{label}</b><br>-------------------<br>📊 <b>Avg Price/m²:</b> %{customdata[0]:,.0f} EGP<br>💰 <b>Avg Total Price:</b> %{customdata[1]:,.0f} EGP<br>📐 <b>Avg Area:</b> %{customdata[2]:,.0f} m²<br>🏠 <b>Properties Count:</b> %{customdata[3]:,.0f}<br>📈 <b>Price Std Dev:</b> %{customdata[4]:,.0f} EGP<br>%{customdata[5]:,.0f} EGP <b>Fair Price</b><br>%{customdata[6]:.2f} <b>Buy Score</b><br>%{customdata[7]}<br>-------------------<br><i>Click to zoom in/out</i>"
            )
            fig15.update_layout(
                margin=dict(t=40, l=25, r=25, b=20),
                coloraxis_colorbar=dict(title="Buy_Score", thickness=20, len=0.75),
            )
            st.plotly_chart(fig15, use_container_width=True)

        recommendations = get_purchase_recommendations(filtered_df)
        st.success(f"### ✅ توصيات الشراء:\n{"\n".join(recommendations)}")

        def create_buy_score_gauge(score):
            fig = go.Figure(
                go.Indicator(
                    mode="gauge+number",
                    value=score,
                    number={"suffix": " / 100"},
                    title={"text": "🏷️ Buy Score"},
                    gauge={
                        "axis": {"range": [0, 100]},
                        "bar": {"color": "#1f77b4"},
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
            )

            return fig

        BUY_SCORE_TOOLTIP = """
            **إزاي بنحسب Buy Score؟**

            • 💰 **تنافسية السعر (40%)** قد إيه أسعار المنطقة مناسبة مقارنة بباقي السوق.

            • 📈 **استقرار السوق (25%)** كل ما تذبذب الأسعار أقل، كل ما المخاطرة أقل.

            • 🏠 **مستوى المعروض (20%)** كل ما عدد العقارات المتاحة أكبر، فرص التفاوض بتكون أفضل.

            • 📐 **قيمة المساحة (15%)** المناطق ذات المساحات المتوسطة والكبيرة بتحتفظ بقيمتها على المدى الطويل.

            • ⚖️ **تعديل السعر العادل (Fair Price)** الدرجة النهائية بتتعدل حسب قرب السعر الفعلي من السعر العادل المتوقع.

            **تفسير الدرجات:**
            🟢 **80 – 100** → فرصة شراء ممتازة  
            🟡 **65 – 79** → خيار جيد (يفضل التفاوض)  
            🟠 **50 – 64** → سعر عادل  
            🔴 **أقل من 50** → السعر مرتفع مقارنة بالسوق
            """

        st.subheader("🏷️ Buy Recommendation")

        col1, col2 = st.columns([1, 1])

        with col1:
            avg_buy_score = treemap_data["Buy_Score"].mean()
            st.plotly_chart(
                create_buy_score_gauge(avg_buy_score),
                use_container_width=True,
            )
            if avg_buy_score >= 80:
                st.success("✅ فرصة شراء ممتازة في المناطق المختارة.")
            elif avg_buy_score >= 65:
                st.warning("🟡 خيارات جيدة متاحة – حاول التفاوض للحصول على سعر أفضل.")
            elif avg_buy_score >= 50:
                st.info("🟠 السوق عادل حاليًا – قارن بين الخيارات بحذر.")
            else:
                st.error("🔴 الأسعار مرتفعة – يُفضَّل الانتظار أو التفاوض بقوة.")

        with col2:
            st.markdown("### ℹ️ Buy Score Explanation")
            st.info(BUY_SCORE_TOOLTIP)

        if "property_distribution" in insights:
            st.write("### 🏘️ Property Type Distribution")
            prop_data = pd.DataFrame(
                {
                    "Type": list(insights["property_distribution"].keys()),
                    "Percentage": list(insights["property_distribution"].values()),
                }
            )
            fig16 = px.pie(
                prop_data,
                values="Percentage",
                names="Type",
                title="Property Type Market Distribution",
            )
            st.plotly_chart(fig16, use_container_width=True)

            avg_price_by_type = (
                filtered_df.groupby("PropertyType")["Price"].mean().reset_index()
            )
            avg_pricem_by_type = (
                filtered_df.groupby("PropertyType")["Price_Per_M"].mean().reset_index()
            )
            col7, col8 = st.columns(2)
            with col7:
                fig17 = px.pie(
                    avg_price_by_type,
                    values="Price",
                    names="PropertyType",
                    title="Average Price by Property Type",
                )
                st.plotly_chart(fig17, use_container_width=True)
            with col8:
                fig18 = px.pie(
                    avg_pricem_by_type,
                    values="Price_Per_M",
                    names="PropertyType",
                    title="Average Price/m² by Property Type",
                )
                st.plotly_chart(fig18, use_container_width=True)


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

st.sidebar.markdown("---")
st.sidebar.subheader("🔄 Auto-Update Status")
st.sidebar.info(
    f"**Last Update:** {st.session_state.get('last_update', 'Checking...')}\n\n**Properties:** {len(df):,}\n**AI Features:** Enabled (Cached)\n**Next Update:** 4:00 AM Egypt Time"
)

st.sidebar.markdown("---")

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
