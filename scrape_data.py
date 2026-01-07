# scrape_data.py
import pandas as pd
import requests
import numpy as np
from bs4 import BeautifulSoup
import time
from datetime import datetime
import os
import sys


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

    # select li cards inside the ul (avoid iterating the ul itself)
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


def scrape_all_pages(base_url, max_pages=20):
    """دالة لجمع البيانات من جميع الصفحات"""
    all_properties = []

    # الصفحة الأولى
    print(f"جاري جمع البيانات من الصفحة 1...")
    page1_properties = scrape_bayut_page(base_url)
    all_properties.extend(page1_properties)
    print(f"تم جمع {len(page1_properties)} عقار من الصفحة 1")

    # الصفحات التالية
    for page_num in range(2, max_pages + 1):
        page_url = f"{base_url.rstrip('/')}/page-{page_num}/"
        print(f"جاري جمع البيانات من الصفحة {page_num}...")

        properties = scrape_bayut_page(page_url)

        # إذا لم نجد عقارات في هذه الصفحة، توقف
        if not properties:
            print(f"لم يتم العثور على عقارات في الصفحة {page_num}. التوقف...")
            break

        all_properties.extend(properties)
        print(f"تم جمع {len(properties)} عقار من الصفحة {page_num}")

        # تأخير بسيط لتجنب حظر IP
        time.sleep(1)

    return all_properties


def clean_data_step1(df_clean):
    """المرحلة الأولى من التنظيف"""
    # Ensure 'Location' exists
    if "Location" not in df_clean.columns:
        return df_clean

    # Split Location into parts and concatenate (drop original Location to avoid duplication)
    df_split = df_clean["Location"].str.split(",", expand=True).add_prefix("Location_")
    df_clean = pd.concat([df_clean.drop(columns=["Location"]), df_split], axis=1)

    # Drop Location_2 if present (some rows may not have 3 parts)
    if "Location_2" in df_clean.columns:
        df_clean = df_clean.drop(columns=["Location_2"])

    # Rename parts to meaningful names
    if "Location_1" in df_clean.columns:
        df_clean = df_clean.rename(columns={"Location_1": "State"})
    else:
        df_clean["State"] = np.nan

    if "Location_0" in df_clean.columns:
        df_clean = df_clean.rename(columns={"Location_0": "Location"})
    else:
        df_clean["Location"] = np.nan

    # Normalize text values safely on the df_clean dataframe
    if "State" in df_clean.columns:
        mask_state = df_clean["State"].notna()
        df_clean.loc[mask_state, "State"] = df_clean.loc[
            mask_state, "State"
        ].str.replace("Saba Pasha", "Saba Basha", case=False, regex=False)
        df_clean.loc[mask_state, "State"] = df_clean.loc[
            mask_state, "State"
        ].str.replace("Borg al-Arab", "Borg El Arab", case=False, regex=False)

    if "Location" in df_clean.columns:
        mask_loc = df_clean["Location"].notna()
        df_clean.loc[mask_loc, "Location"] = df_clean.loc[
            mask_loc, "Location"
        ].str.replace("Smoha", "Smouha", case=False, regex=False)

    return df_clean


# ...existing code...
def clean_data_step2(df_clean):
    """المرحلة الثانية من التنظيف (fixed .str accessor errors)"""
    # Ensure 'State'/'Location' and other text columns are string dtype to safely use .str
    import pandas as _pd

    try:
        # Cast relevant columns to pandas "string" dtype if they exist
        for col in (
            "Location",
            "State",
            "Bedrooms",
            "Bathrooms",
            "Down_Payment",
            "Price",
            "Area",
        ):
            if col in df_clean.columns:
                df_clean[col] = df_clean[col].astype("string")

        # Ensure 'Location' exists
        if "Location" not in df_clean.columns:
            return df_clean

        # Split Location into parts and concatenate (drop original Location to avoid duplication)
        df_clean_split = (
            df_clean["Location"].str.split(",", expand=True).add_prefix("Location_")
        )
        df_clean = _pd.concat(
            [df_clean.drop(columns=["Location"]), df_clean_split], axis=1
        )

        # Drop Location_2 if present (some rows may not have 3 parts)
        if "Location_2" in df_clean.columns:
            df_clean = df_clean.drop(columns=["Location_2"])

        # Rename parts to meaningful names
        if "Location_1" in df_clean.columns:
            df_clean = df_clean.rename(columns={"Location_1": "State"})
        else:
            df_clean["State"] = _pd.NA

        if "Location_0" in df_clean.columns:
            df_clean = df_clean.rename(columns={"Location_0": "Location"})
        else:
            df_clean["Location"] = _pd.NA

        # Normalize text values safely on the df_clean dataframe
        if "State" in df_clean.columns:
            mask_state = df_clean["State"].notna()
            df_clean.loc[mask_state, "State"] = df_clean.loc[
                mask_state, "State"
            ].str.replace("Saba Pasha", "Saba Basha", case=False, regex=False)
            df_clean.loc[mask_state, "State"] = df_clean.loc[
                mask_state, "State"
            ].str.replace("Borg al-Arab", "Borg El Arab", case=False, regex=False)

        if "Location" in df_clean.columns:
            mask_loc = df_clean["Location"].notna()
            df_clean.loc[mask_loc, "Location"] = df_clean.loc[
                mask_loc, "Location"
            ].str.replace("Smoha", "Smouha", case=False, regex=False)

        # Fixing 'Price' column type casting error
        if "Price" in df_clean.columns:
            df_clean["Price"] = df_clean["Price"].str.replace(",", "").astype("int64")

        # Change column type to object for column: 'Area'
        if "Area" in df_clean.columns:
            df_clean["Area"] = df_clean["Area"].str.replace(",", "").astype("int")

        # Bedrooms/Bathrooms replacements (safe because cast to string dtype above)
        if "Bedrooms" in df_clean.columns:
            df_clean["Bedrooms"] = df_clean["Bedrooms"].str.replace(
                "+ Maid", " ", case=False, regex=False
            )
            df_clean["Bedrooms"] = df_clean["Bedrooms"].str.replace(
                "+", "", case=False, regex=False
            )
            df_clean["Bedrooms"] = df_clean["Bedrooms"].str.replace(
                "studio ", "1", case=False, regex=False
            )
            df_clean["Bedrooms"] = df_clean["Bedrooms"].str.replace(
                ".0", "", case=False, regex=False
            )
            df_clean = df_clean.astype({"Bedrooms": "int8"})

        if "Bathrooms" in df_clean.columns:
            df_clean["Bathrooms"] = df_clean["Bathrooms"].str.replace(
                "+", "", case=False, regex=False
            )
            df_clean["Bathrooms"] = df_clean["Bathrooms"].str.replace(
                ".0", "", case=False, regex=False
            )
            df_clean = df_clean.astype({"Bathrooms": "int8"})

        # Down_Payment cleaning
        if "Down_Payment" in df_clean.columns:
            df_clean["Down_Payment"] = df_clean["Down_Payment"].str.replace(
                " EGP", "", case=False, regex=False
            )
            df_clean["Down_Payment"] = df_clean["Down_Payment"].str.replace(
                "EGP", "", case=False, regex=False
            )
            df_clean["Down_Payment"] = df_clean["Down_Payment"].str.replace(
                "0% Down Payment", "0", case=False, regex=False
            )
            df_clean["Down_Payment"] = df_clean["Down_Payment"].str.replace(
                " 50 monthly / 1 year", "0", case=False, regex=False
            )
            df_clean["Down_Payment"] = df_clean["Down_Payment"].str.replace(
                "monthly / 1.5 years", "", case=False, regex=False
            )
            for years in range(1, 13):
                pattern = (
                    f"monthly / {years} years" if years > 1 else "monthly / 1 year"
                )
                df_clean["Down_Payment"] = df_clean["Down_Payment"].str.replace(
                    pattern, "", case=False, regex=False
                )
            df_clean["Down_Payment"] = df_clean["Down_Payment"].str.replace(",", "")
            df_clean["Down_Payment"] = df_clean["Down_Payment"].astype("int64")

        # Calculate Price_Per_M
        df_clean["Price_Per_M"] = df_clean["Price"] / df_clean["Area"]
        df_clean = df_clean.round({"Price_Per_M": 2})

        return df_clean

    except Exception as e:
        print(f"❌ Error in clean_data_step2: {e}")
        import traceback

        traceback.print_exc()
        return df_clean


# ...existing code...


def process_and_save_data(df_raw, output_path):
    """معالجة وحفظ البيانات"""
    print("🔄 بدء معالجة البيانات...")

    # المرحلة الأولى من التنظيف
    df_clean_1 = clean_data_step1(df_raw.copy())
    df1 = df_clean_1.copy()

    # معالجة Down_Payment
    df1["Down_Payment"] = df1["Down_Payment"].fillna(0)

    # إزالة الصفوف الفارغة
    initial_count = len(df1)
    df1.dropna(inplace=True)
    df1.reset_index(drop=True, inplace=True)
    print(f"✅ تمت إزالة {initial_count - len(df1)} صف فارغ")

    # تنظيف إضافي للموقع
    df_clean = df1.copy()
    df_clean["State"] = df_clean["State"].str.strip()

    # تصحيح البيانات إذا كانت State تحتوي على "Alexandria"
    mask = df_clean["State"].str.contains("Alexandria", case=False, na=False)
    df_clean.loc[mask, "State"] = df_clean.loc[mask, "Location"]
    df_clean["State"] = df_clean["State"].fillna(df_clean["Location"])

    # تنظيف النصوص
    df_clean["State"] = df_clean["State"].str.strip()
    df_clean["Location"] = df_clean["Location"].str.strip()

    # إضافة Payment_Method
    df_clean["Payment_Method"] = ""
    df_clean.loc[
        df_clean["Down_Payment"].astype(str).str.strip() != "0", "Payment_Method"
    ] = "Installments"
    df_clean.loc[df_clean["Payment_Method"] == "", "Payment_Method"] = "Cash"

    # المرحلة الثانية من التنظيف
    df_clean = clean_data_step2(df_clean)

    # إضافة تاريخ الجمع
    # df_clean["Scraped_Date"] = datetime.now().strftime("%Y-%m-%d")

    # قراءة البيانات القديمة إذا وجدت
    if os.path.exists(output_path):
        try:
            df_final = pd.read_csv(output_path)
            print(f"📁 تم العثور على بيانات موجودة: {len(df_final)} عقار")

            # دمج البيانات
            df_combined = pd.concat([df_final, df_clean], ignore_index=True)

            # إزالة التكرارات
            initial_combined = len(df_combined)
            df_combined.drop_duplicates(inplace=True)
            duplicates_removed = initial_combined - len(df_combined)

            if duplicates_removed > 0:
                print(f"🔄 تمت إزالة {duplicates_removed} عقار مكرر")

            # حفظ البيانات
            df_combined.to_csv(output_path, index=False)
            print(f"💾 تم حفظ {len(df_combined)} عقار في {output_path}")
            print(
                f"📈 التغيير الصافي: {len(df_clean) - duplicates_removed:+d} عقار جديد"
            )

        except Exception as e:
            print(f"⚠️ خطأ في قراءة/حفظ البيانات القديمة: {e}")
            # حفظ البيانات الجديدة فقط
            df_clean.to_csv(output_path, index=False)
            print(f"💾 تم حفظ {len(df_clean)} عقار في {output_path} (ملف جديد)")
    else:
        # حفظ البيانات الجديدة
        df_clean.to_csv(output_path, index=False)
        print(f"💾 تم حفظ {len(df_clean)} عقار في {output_path} (ملف جديد)")

    return df_clean


def main():
    """الدالة الرئيسية"""
    print("🚀 بدء جمع بيانات العقارات من Bayut")
    print("=" * 50)
    print(f"📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # إعدادات
    base_url = "https://www.bayut.eg/en/alexandria/properties-for-sale/"
    max_pages = 50  # عدد الصفحات المطلوب جمعها
    output_path = "Final1.csv"  # مسار حفظ البيانات

    # جمع البيانات
    print(f"\n📥 جاري جمع البيانات من {max_pages} صفحات...")
    all_properties = scrape_all_pages(base_url, max_pages=max_pages)

    if not all_properties:
        print("❌ لم يتم جمع أي عقارات!")
        return False

    # تحويل إلى DataFrame
    df_raw = pd.DataFrame(all_properties)
    print(f"\n📊 إجمالي العقارات المجمعة: {len(df_raw)} عقار")

    # معالجة وحفظ البيانات
    df_final = process_and_save_data(df_raw, output_path)

    # عرض ملخص
    print("\n" + "=" * 50)
    print("📋 ملخص العملية:")
    print("=" * 50)
    print(f"العقارات المجمعة: {len(df_raw)}")
    print(f"العقارات بعد التنظيف: {len(df_final)}")
    print(f"متوسط السعر: {df_final['Price'].mean():,.0f} EGP")
    print(f"طرق الدفع:")
    print(f"  - نقداً: {(df_final['Payment_Method'] == 'Cash').sum()}")
    print(f"  - تقسيط: {(df_final['Payment_Method'] == 'Installments').sum()}")
    print("=" * 50)
    print("✅ اكتملت عملية الجمع بنجاح!")

    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️ تم إيقاف العملية بواسطة المستخدم")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ خطأ غير متوقع: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
