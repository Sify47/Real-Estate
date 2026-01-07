import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
import os


def scrape_bayut_page(page_url):
    """دالة لجمع البيانات من صفحة واحدة"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        response = requests.get(page_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
    except Exception as e:
        print(f"خطأ في تحميل الصفحة {page_url}: {e}")
        return []

    def text_or_none(selector, parent):
        el = parent.select_one(selector)
        return el.get_text(strip=True) if el else None

    property_cards = soup.select("ul._172b35d1 li")
    properties = []

    for card in property_cards:
        try:
            a = card.select_one("a._8969fafd")
            link = (
                f"https://www.bayut.eg{a.get('href')}" if a and a.get("href") else None
            )

            price = text_or_none(
                "h4.afdad5da._71366de7 span.eff033a6", card
            ) or text_or_none("span.eff033a6", card)
            title = text_or_none("h2._34c51035", card)

            spans = card.select("span._3002c6fb")
            type_ = spans[0].get_text(strip=True) if len(spans) > 0 else None
            bedrooms = spans[1].get_text(strip=True) if len(spans) > 1 else None
            bathrooms = spans[2].get_text(strip=True) if len(spans) > 2 else None

            location = text_or_none("h3._51c6b1ca", card)
            d = text_or_none("span.fd7ade6e", card)

            area_raw = text_or_none("h4._60820635._07b5f28e", card) or text_or_none(
                "h4", card
            )
            area = area_raw[:-6] if area_raw and len(area_raw) > 6 else area_raw

            properties.append(
                {
                    "PropertyType": type_,
                    "Link": link,
                    "Title": title,
                    "Price": price,
                    "Location": location,
                    "Area": area,
                    "Bedrooms": bedrooms,
                    "Bathrooms": bathrooms,
                    "Down_Payment": d,
                }
            )
        except Exception as e:
            print(f"خطأ في معالجة كارد: {e}")
            continue

    return properties


def clean_scraped_data(df_clean):
    """دالة لتنظيف البيانات المجمعة"""
    try:
        df_temp = df_clean.copy()

        # تنظيف Location
        if "Location" in df_temp.columns:
            df_split = (
                df_temp["Location"]
                .astype(str)
                .str.split(",", expand=True)
                .add_prefix("Location_")
            )
            df_temp = pd.concat([df_temp.drop(columns=["Location"]), df_split], axis=1)

            if "Location_1" in df_temp.columns:
                df_temp = df_temp.rename(columns={"Location_1": "State"})
            else:
                df_temp["State"] = np.nan

            if "Location_0" in df_temp.columns:
                df_temp = df_temp.rename(columns={"Location_0": "Location"})
            else:
                df_temp["Location"] = np.nan

        # تنظيف النصوص
        if "State" in df_temp.columns:
            mask_state = df_temp["State"].notna()
            df_temp.loc[mask_state, "State"] = (
                df_temp.loc[mask_state, "State"]
                .astype(str)
                .str.replace("Saba Pasha", "Saba Basha", case=False, regex=False)
            )
            df_temp.loc[mask_state, "State"] = (
                df_temp.loc[mask_state, "State"]
                .astype(str)
                .str.replace("Borg al-Arab", "Borg El Arab", case=False, regex=False)
            )

        if "Location" in df_temp.columns:
            mask_loc = df_temp["Location"].notna()
            df_temp.loc[mask_loc, "Location"] = (
                df_temp.loc[mask_loc, "Location"]
                .astype(str)
                .str.replace("Smoha", "Smouha", case=False, regex=False)
            )

        # تنظيف السعر
        if "Price" in df_temp.columns:
            df_temp["Price"] = (
                df_temp["Price"]
                .astype(str)
                .str.replace(",", "")
                .str.replace("EGP", "")
                .str.strip()
            )
            df_temp["Price"] = pd.to_numeric(df_temp["Price"], errors="coerce")

        # تنظيف المساحة
        if "Area" in df_temp.columns:
            df_temp["Area"] = (
                df_temp["Area"]
                .astype(str)
                .str.replace(",", "")
                .str.replace("m²", "")
                .str.strip()
            )
            df_temp["Area"] = pd.to_numeric(df_temp["Area"], errors="coerce")

        # تنظيف Bedrooms
        if "Bedrooms" in df_temp.columns:
            df_temp["Bedrooms"] = df_temp["Bedrooms"].astype(str)
            replacements = [("\+ Maid", " "), ("\+", ""), ("studio ", "1"), (".0", "")]
            for old, new in replacements:
                df_temp["Bedrooms"] = df_temp["Bedrooms"].str.replace(
                    old, new, case=False, regex=False
                )
            df_temp["Bedrooms"] = pd.to_numeric(df_temp["Bedrooms"], errors="coerce")

        # تنظيف Bathrooms
        if "Bathrooms" in df_temp.columns:
            df_temp["Bathrooms"] = df_temp["Bathrooms"].astype(str)
            df_temp["Bathrooms"] = df_temp["Bathrooms"].str.replace(
                "\+", "", case=False, regex=False
            )
            df_temp["Bathrooms"] = df_temp["Bathrooms"].str.replace(
                ".0", "", case=False, regex=False
            )
            df_temp["Bathrooms"] = pd.to_numeric(df_temp["Bathrooms"], errors="coerce")

        # تنظيف Down_Payment
        if "Down_Payment" in df_temp.columns:
            df_temp["Down_Payment"] = df_temp["Down_Payment"].astype(str)
            replacements = [
                (" EGP", ""),
                ("EGP", ""),
                ("monthly / \d+ years?", ""),
                ("0% Down Payment", "0"),
                (" 50 monthly / 1 year", "0"),
                (",", ""),
            ]
            for old, new in replacements:
                df_temp["Down_Payment"] = df_temp["Down_Payment"].str.replace(
                    old, new, case=False, regex=True
                )
            df_temp["Down_Payment"] = pd.to_numeric(
                df_temp["Down_Payment"], errors="coerce"
            )
            df_temp["Down_Payment"] = df_temp["Down_Payment"].fillna(0)

        # حساب Price_Per_M
        if "Price" in df_temp.columns and "Area" in df_temp.columns:
            df_temp["Price_Per_M"] = df_temp["Price"] / df_temp["Area"]
            df_temp["Price_Per_M"] = df_temp["Price_Per_M"].round(2)

        # إضافة Payment_Method
        if "Down_Payment" in df_temp.columns:
            df_temp["Payment_Method"] = "Cash"
            if not df_temp.empty:
                df_temp.loc[df_temp["Down_Payment"] > 0, "Payment_Method"] = (
                    "Installments"
                )
        df_temp.dropna(inplace=True)
        return df_temp

    except Exception as e:
        print(f"Error in cleaning data: {e}")
        return df_clean


def main():
    print("🚀 Starting automatic real estate scraping...")
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # جمع البيانات
    base_url = "https://www.bayut.eg/en/alexandria/properties-for-sale/"
    all_properties = []

    # جمع من 3 صفحات
    for page_num in range(1, 31):
        if page_num == 1:
            page_url = base_url
        else:
            page_url = f"{base_url.rstrip('/')}/page-{page_num}/"

        print(f"📄 Scraping page {page_num}...")
        properties = scrape_bayut_page(page_url)

        if not properties:
            print(f"⚠️ No properties found on page {page_num}")
            break

        all_properties.extend(properties)
        print(f"✅ Collected {len(properties)} properties from page {page_num}")

        time.sleep(2)  # تأخير لتجنب الحظر

    if all_properties:
        # تحويل إلى DataFrame
        df_scraped = pd.DataFrame(all_properties)
        print(f"📊 Total properties collected: {len(df_scraped)}")

        # تنظيف البيانات
        df_cleaned = clean_scraped_data(df_scraped)

        if not df_cleaned.empty:
            # قراءة البيانات القديمة إذا وجدت
            if os.path.exists("Final1.csv"):
                try:
                    existing_df = pd.read_csv("Final1.csv")
                    print(f"📁 Found existing data with {len(existing_df)} properties")

                    # دمج البيانات (إزالة التكرارات)
                    combined_df = pd.concat(
                        [existing_df, df_cleaned], ignore_index=True
                    )

                    # إزالة التكرارات بناءً على العنوان والموقع والسعر
                    combined_df = combined_df.drop(
                        columns=["Location_2"], errors="ignore"
                    )
                    combined_df = combined_df.drop_duplicates()
                    print(
                        f"🔄 After merging and deduplication: {len(combined_df)} properties"
                    )
                except Exception as e:
                    print(f"⚠️ Error reading existing data: {e}")
                    combined_df = df_cleaned
            else:
                combined_df = df_cleaned
                print("🆕 No existing data found, creating new file")

            # حفظ البيانات
            combined_df.to_csv("Final1.csv", index=False, encoding="utf-8")
            print(f"💾 Saved {len(combined_df)} properties to Final1.csv")

            # حفظ metadata
            with open("scraping_metadata.txt", "w") as f:
                f.write(
                    f"Last scraped: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                )
                f.write(f"Total properties: {len(combined_df)}\n")
                f.write(f"Pages scraped: {min(page_num, 3)}\n")

            print("✅ Scraping completed successfully!")
            return True
        else:
            print("⚠️ No valid data after cleaning")
            return False
    else:
        print("❌ No properties collected")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
