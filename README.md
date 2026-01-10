# 🏠 Real Estate Market Analysis Dashboard

An end-to-end **Data Analytics & Decision Support Dashboard** designed to help buyers understand the Egyptian real estate market and make smarter purchase decisions.

---

## 🎯 Problem Statement
The average real estate buyer in Egypt struggles to:
- Identify fair property prices
- Compare locations objectively
- Understand market stability
- Decide whether a property is worth buying or overpriced

---

## 💡 Solution
This project provides an **interactive dashboard** that transforms raw market data into:
- Fair Price estimation
- Buy / Avoid recommendations
- Market insights tailored for non-technical users

Built using Python and Streamlit with integrated analytics and machine learning.

---

## 🛠️ Tools & Technologies
- **Python**
- **Pandas, NumPy**
- **BeautifulSoup** (Web Scraping)
- **Plotly** (Interactive Visualizations)
- **Streamlit** (Dashboard)
- **Scikit-learn** (Random Forest Regression)
- **GitHub** (Data Hosting & Version Control)

---

## 🧲 Data Collection & Cleaning Pipeline

### 🔍 Data Sources
- **PropertyFinder Egypt**
- **Bayut Egypt**

Listings are collected automatically using a custom Python scraping pipeline.

---

### 🛠️ Web Scraping
- Built with `requests` and `BeautifulSoup`
- Handles pagination and HTML inconsistencies
- Uses custom user-agent headers
- Includes rate limiting to avoid IP blocking
- Error handling per page and per listing

**Extracted fields include:**
- Property Type  
- Title  
- Price  
- Area (m²)  
- Bedrooms & Bathrooms  
- Location & State  
- Down Payment  
- Payment Method (Cash / Installments)  
- Listing URL  

---

### 🧹 Data Cleaning & Feature Engineering
Cleaning is performed in two stages:

**Stage 1 – Location Normalization**
- Parses raw location strings into `Location` and `State`
- Handles inconsistent formats
- Fixes naming issues (e.g. *Smoha → Smouha*)

**Stage 2 – Data Standardization**
- Converts numeric fields safely
- Handles special text cases (studio, maid room, installment terms)
- Removes incomplete records
- Creates derived features:
  - **Price per m²**
  - **Payment Method classification**

---

### 🔄 Deduplication & Updates
- Merges new data with existing records
- Removes duplicates based on listing URL
- Keeps the latest version of each property

---


## 📊 Key Features
- Dynamic filters (Location, Price, Area, Bedrooms, Payment Method)
- Average Price & Price per m² analysis
- Price vs Area insights
- Market stability & supply indicators
- **Fair Price Estimation** (Rule-based + ML fallback)
- **Buy Score (0–100)** decision system
- Area-level recommendations
- Buyer-friendly storytelling in Arabic
- Auto-updating data pipeline

---

## 🤖 Fair Price Estimation
Fair Price is calculated using:
- Market average price per m²
- Property characteristics (Area, Bedrooms, Bathrooms)
- Machine Learning model (Random Forest) when sufficient data is available

Fallback logic ensures reliable results even with limited data.

---

## 🟢 Buy Score Logic
Buy Score combines multiple business-driven factors:
- Price competitiveness
- Market stability
- Supply level
- Area value
- Fair price comparison

Final score is normalized to **0–100** with clear labels:
- 🟢 Excellent Deal
- 🟡 Good Option
- 🟠 Fair
- 🔴 Overpriced

---

## 📈 Key Insights
- Best value properties typically range between **90–120 m²**
- Some mid-priced areas offer higher demand and better resale value
- High price volatility indicates higher purchase risk
- Installment-based properties dominate buyer preference

---

## 📌 Business Impact
- Helps buyers avoid overpriced properties
- Reduces decision risk using data-driven insights
- Transforms complex analytics into actionable recommendations

---

## 🚀 Future Improvements
- Buy Score Gauge visualization
- Price negotiation range suggestion
- Area growth forecasting
- Personalized buyer profile
- ML-powered price prediction per listing

---

## 👤 Author
**Mohamed Elsify**  
Data Analyst | Python | Power BI | Streamlit  
