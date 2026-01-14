# scrape_data.py
import pandas as pd
import requests
import numpy as np
from bs4 import BeautifulSoup
import time
from datetime import datetime
import os
import sys


def scrape_propertyfinder_page(page_url):
    """دالة لجمع البيانات من صفحة واحدة في PropertyFinder"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        response = requests.get(page_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
    except Exception as e:
        print(f"خطأ في تحميل صفحة PropertyFinder {page_url}: {e}")
        return []

    def text_or_none(selector, parent):
        el = parent.select_one(selector)
        return el.get_text(strip=True) if el else None

    property_cards = soup.select("ul.styles_desktop_container__V85pq li")
    properties = []

    for card in property_cards:
        try:
            a = card.select_one("a.styles-module_property-card__link__r--GK")
            link = (
                f"https://www.propertyfinder.eg{a.get('href')}"
                if a and a.get("href")
                else None
            )

            # الحصول على السعر
            price_element = card.select_one("div.styles-module_content__price__TBYWv p")
            price = price_element.get_text(strip=True) if price_element else None

            # تنظيف السعر مباشرة هنا
            if price:
                price = (
                    price.replace("EGP", "").replace(",", "").replace(" ", "").strip()
                )

            title = text_or_none("h3.styles-module_content__title__pLLTh", card)
            type_ = text_or_none(
                "p.styles-module_content__property-type__qxCMa span", card
            )

            # استخدام data-testid للبحث عن المواصفات
            bedrooms = text_or_none('[data-testid="property-card-spec-bedroom"]', card)
            bathrooms = text_or_none(
                '[data-testid="property-card-spec-bathroom"]', card
            )

            # تصحيح معالجة المساحة
            area_raw = text_or_none('[data-testid="property-card-spec-area"]', card)
            if area_raw:
                # إزالة "m²" والحروف غير رقمية
                area = "".join(filter(str.isdigit, area_raw.replace(",", "")))
            else:
                area = None

            location = text_or_none("p.styles-module_content__location__yBL3r", card)

            # البحث عن Down Payment
            down_payment_element = card.select_one("div.tag-module_tag__jFU3w")
            if down_payment_element:
                Down_Payment = down_payment_element.get_text(strip=True)
                # تنظيف النص
                Down_Payment = Down_Payment.replace("EGP", "").replace(",", "").strip()
            else:
                Down_Payment = "0"

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
                    "Down_Payment": Down_Payment,
                    "Payment_Method": "Installments" if Down_Payment != "0" else "Cash",
                }
            )
        except Exception as e:
            print(f"خطأ في معالجة كارد PropertyFinder: {e}")
            continue

    return properties


def scrape_bayut_page(page_url):
    """دالة لجمع البيانات من صفحة واحدة في Bayut"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        response = requests.get(page_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
    except Exception as e:
        print(f"خطأ في تحميل صفحة Bayut {page_url}: {e}")
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
            if area_raw and len(area_raw) > 6:
                area = area_raw[:-6]
            else:
                area = area_raw

            # تنظيف السعر
            if price:
                price = price.replace(",", "").replace("EGP", "").strip()

            # تنظيف Down Payment
            if d:
                Down_Payment = d.replace("EGP", "").replace(",", "").strip()
                Payment_Method = (
                    "Installments"
                    if Down_Payment != "0" and Down_Payment != ""
                    else "Cash"
                )
            else:
                Down_Payment = "0"
                Payment_Method = "Cash"

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
                    "Down_Payment": Down_Payment,
                    "Payment_Method": Payment_Method,
                }
            )
        except Exception as e:
            print(f"خطأ في معالجة كارد Bayut: {e}")
            continue

    return properties


def scrape_all_propertyfinder_pages(base_url, max_pages=3):
    """دالة لجمع البيانات من جميع صفحات PropertyFinder"""
    all_properties = []

    # الصفحة الأولى
    print(f"جاري جمع البيانات من PropertyFinder الصفحة 1...")
    page1_properties = scrape_propertyfinder_page(base_url)
    all_properties.extend(page1_properties)
    print(f"تم جمع {len(page1_properties)} عقار من PropertyFinder الصفحة 1")

    # الصفحات التالية
    for page_num in range(2, max_pages + 1):
        page_url = f"{base_url}page={page_num}"
        print(f"جاري جمع البيانات من PropertyFinder الصفحة {page_num}...")

        properties = scrape_propertyfinder_page(page_url)

        # إذا لم نجد عقارات في هذه الصفحة، توقف
        if not properties:
            print(
                f"لم يتم العثور على عقارات في PropertyFinder الصفحة {page_num}. التوقف..."
            )
            break

        all_properties.extend(properties)
        print(f"تم جمع {len(properties)} عقار من PropertyFinder الصفحة {page_num}")

        # تأخير بسيط لتجنب حظر IP
        time.sleep(1)

    return all_properties


def scrape_all_bayut_pages(base_url, max_pages=40):
    """دالة لجمع البيانات من جميع صفحات Bayut"""
    all_properties = []

    # الصفحة الأولى
    print(f"جاري جمع البيانات من Bayut الصفحة 1...")
    page1_properties = scrape_bayut_page(base_url)
    all_properties.extend(page1_properties)
    print(f"تم جمع {len(page1_properties)} عقار من Bayut الصفحة 1")

    # الصفحات التالية
    for page_num in range(2, max_pages + 1):
        page_url = f"{base_url.rstrip('/')}/page-{page_num}/"
        print(f"جاري جمع البيانات من Bayut الصفحة {page_num}...")

        properties = scrape_bayut_page(page_url)

        # إذا لم نجد عقارات في هذه الصفحة، توقف
        if not properties:
            print(f"لم يتم العثور على عقارات في Bayut الصفحة {page_num}. التوقف...")
            break

        all_properties.extend(properties)
        print(f"تم جمع {len(properties)} عقار من Bayut الصفحة {page_num}")

        # تأخير بسيط لتجنب حظر IP
        time.sleep(1)

    return all_properties


def clean_data_step1(df_clean):
    """المرحلة الأولى من التنظيف"""
    # Ensure 'Location' exists
    if "Location" not in df_clean.columns:
        return df_clean

    # Split Location into parts and concatenate
    df_split = df_clean["Location"].str.split(",", expand=True).add_prefix("Location_")
    df_clean = pd.concat([df_clean.drop(columns=["Location"]), df_split], axis=1)

    # التعامل مع التنسيقات المختلفة
    num_columns = df_split.shape[1]

    # دايماً نأخذ أول جزء كـ Location
    if "Location_0" in df_clean.columns:
        location_value = df_split["Location_0"].str.strip()
        df_clean["Location"] = location_value
    else:
        df_clean["Location"] = np.nan

    # تحديد State بناءً على عدد الأجزاء
    if num_columns >= 3:
        # حالة 3 أجزاء: نأخذ الجزء الثاني
        if "Location_1" in df_clean.columns:
            df_clean["State"] = df_split["Location_1"].str.strip()
        else:
            df_clean["State"] = df_clean["Location"]  # إذا مش موجود، ناخد Location
    elif num_columns >= 2:
        # حالة جزئين: State تكون نفس Location
        df_clean["State"] = df_clean["Location"]
    elif num_columns >= 1:
        # حالة جزء واحد: State تكون نفس Location
        df_clean["State"] = df_clean["Location"]
    else:
        df_clean["State"] = np.nan

    # حذف الأعمدة المؤقتة
    for col in ["Location_0", "Location_1", "Location_2"]:
        if col in df_clean.columns:
            df_clean = df_clean.drop(columns=[col])

    # Normalize text values
    if "State" in df_clean.columns:
        mask_state = df_clean["State"].notna()
        df_clean.loc[mask_state, "State"] = df_clean.loc[
            mask_state, "State"
        ].str.replace("Saba Pasha", "Saba Basha", case=False, regex=False)
        df_clean.loc[mask_state, "State"] = df_clean.loc[
            mask_state, "State"
        ].str.replace("Borg al-Arab", "Borg El Arab", case=False, regex=False)
        df_clean.loc[mask_state, "State"] = df_clean.loc[
            mask_state, "State"
        ].str.replace("Smoha", "Smouha", case=False, regex=False)
        df_clean.loc[mask_state, "State"] = df_clean.loc[
            mask_state, "State"
        ].str.replace("Alex West", "Agami", case=False, regex=False)
        df_clean.loc[mask_state, "State"] = df_clean.loc[
            mask_state, "State"
        ].str.replace("Borg El Arab City", "Borg El Arab", case=False, regex=False)

    if "Location" in df_clean.columns:
        mask_loc = df_clean["Location"].notna()
        df_clean.loc[mask_loc, "Location"] = df_clean.loc[
            mask_loc, "Location"
        ].str.replace("Smoha", "Smouha", case=False, regex=False)
        df.loc[mask_loc, "Location"] = df.loc[
                    mask_loc, "Location"
                ].str.replace("Palm Hills Alexandria", "Palm Hills", case=False, regex=False)
        df.loc[mask_loc, "Location"] = df.loc[
                    mask_loc, "Location"
                ].str.replace("Borg al-Arab", "Borg El Arab", case=False, regex=False)
        df.loc[df["Location"] == "Palm Hills", "State"] = "Palm Hills"
    df_clean["State"] = df_clean["State"].str.strip()
    mask = df_clean["State"].str.contains("Alexandria", case=False, na=False)
    mask1 = df_clean["State"].str.contains("Hay Sharq", case=False, na=False)
    df_clean.loc[mask, "State"] = df_clean.loc[mask, "Location"]
    df_clean.loc[mask1, "State"] = df_clean.loc[mask1, "Location"]
    df_clean["State"] = df_clean["State"].fillna(df_clean["Location"])
    return df_clean


def clean_data_step2(df_clean):
    """المرحلة الثانية من التنظيف"""
    try:
        # 1. تأكد أن الأعمدة النصية هي string dtype
        text_columns = [
            "Location",
            "State",
            "Bedrooms",
            "Bathrooms",
            "Down_Payment",
            "Price",
            "Area",
            "PropertyType",
            "Title",
        ]
        for col in text_columns:
            if col in df_clean.columns:
                df_clean[col] = df_clean[col].astype("string")

        # 2. تنظيف وتطبيع النصوص
        if "State" in df_clean.columns:
            df_clean["State"] = df_clean["State"].str.replace(
                "Saba Pasha", "Saba Basha", case=False, regex=False
            )
            df_clean["State"] = df_clean["State"].str.replace(
                "Borg al-Arab", "Borg El Arab", case=False, regex=False
            )
            df_clean["State"] = df_clean["State"].str.replace(
                "Smoha", "Smouha", case=False, regex=False
            )

        if "Location" in df_clean.columns:
            df_clean["Location"] = df_clean["Location"].str.replace(
                "Smoha", "Smouha", case=False, regex=False
            )

        # 3. تنظيف Price
        if "Price" in df_clean.columns:
            df_clean["Price"] = df_clean["Price"].str.replace(",", "", regex=False)
            df_clean["Price"] = df_clean["Price"].str.replace("EGP", "", regex=False)
            df_clean["Price"] = pd.to_numeric(df_clean["Price"], errors="coerce")

        # 4. تنظيف Area
        if "Area" in df_clean.columns:
            df_clean["Area"] = df_clean["Area"].str.replace(",", "", regex=False)
            df_clean["Area"] = df_clean["Area"].str.replace("m²", "", regex=False)
            df_clean["Area"] = df_clean["Area"].str.replace("m", "", regex=False)
            df_clean["Area"] = pd.to_numeric(df_clean["Area"], errors="coerce")

        # 5. تنظيف Bedrooms
        if "Bedrooms" in df_clean.columns:
            df_clean["Bedrooms"] = df_clean["Bedrooms"].str.replace(
                "+ Maid", "", case=False, regex=False
            )
            df_clean["Bedrooms"] = df_clean["Bedrooms"].str.replace(
                "+", "", case=False, regex=False
            )
            df_clean["Bedrooms"] = df_clean["Bedrooms"].str.replace(
                "studio", "1", case=False, regex=False
            )
            df_clean["Bedrooms"] = df_clean["Bedrooms"].str.replace(
                ".0", "", case=False, regex=False
            )
            df_clean["Bedrooms"] = pd.to_numeric(df_clean["Bedrooms"], errors="coerce")

        # 6. تنظيف Bathrooms
        if "Bathrooms" in df_clean.columns:
            df_clean["Bathrooms"] = df_clean["Bathrooms"].str.replace(
                "+", "", case=False, regex=False
            )
            df_clean["Bathrooms"] = df_clean["Bathrooms"].str.replace(
                ".0", "", case=False, regex=False
            )
            df_clean["Bathrooms"] = pd.to_numeric(
                df_clean["Bathrooms"], errors="coerce"
            )

        # 7. تنظيف Down_Payment
        if "Down_Payment" in df_clean.columns:
            df_clean["Down_Payment"] = df_clean["Down_Payment"].astype(str)
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

            for years in range(1, 13):
                pattern = (
                    f"monthly / {years} years" if years > 1 else "monthly / 1 year"
                )
                df_clean["Down_Payment"] = df_clean["Down_Payment"].str.replace(
                    pattern, "", case=False, regex=False
                )

            df_clean["Down_Payment"] = df_clean["Down_Payment"].str.replace(
                ",", "", regex=False
            )
            df_clean["Down_Payment"] = pd.to_numeric(
                df_clean["Down_Payment"], errors="coerce"
            ).fillna(0)

        # 8. حساب Price_Per_M
        if "Price" in df_clean.columns and "Area" in df_clean.columns:
            mask = df_clean["Area"] > 0
            df_clean.loc[mask, "Price_Per_M"] = (
                df_clean.loc[mask, "Price"] / df_clean.loc[mask, "Area"]
            )
            df_clean["Price_Per_M"] = df_clean["Price_Per_M"].round(2)

        # 9. إضافة تاريخ الجمع

        return df_clean

    except Exception as e:
        print(f"❌ Error in clean_data_step2: {e}")
        import traceback

        traceback.print_exc()
        return df_clean


def process_and_save_data(df_raw, output_path):
    """معالجة وحفظ البيانات"""
    print("🔄 بدء معالجة البيانات...")

    # المرحلة الأولى من التنظيف
    df_clean_1 = clean_data_step1(df_raw.copy())
    df1 = df_clean_1.copy()

    # معالجة Down_Payment
    if "Down_Payment" in df1.columns:
        df1["Down_Payment"] = df1["Down_Payment"].fillna(0)

    # إزالة الصفوف الفارغة
    initial_count = len(df1)
    required_columns = ["Location", "State", "Price", "Area"]
    for col in required_columns:
        if col in df1.columns:
            df1 = df1[df1[col].notna() & (df1[col] != "")]

    df1.reset_index(drop=True, inplace=True)
    print(f"✅ تمت إزالة {initial_count - len(df1)} صف فارغ")

    # تنظيف إضافي
    df_clean = df1.copy()
    if "State" in df_clean.columns:
        df_clean["State"] = df_clean["State"].str.strip()
    if "Location" in df_clean.columns:
        df_clean["Location"] = df_clean["Location"].str.strip()

    # إضافة Payment_Method إذا لم تكن موجودة
    if "Payment_Method" not in df_clean.columns:
        df_clean["Payment_Method"] = "Cash"
        if "Down_Payment" in df_clean.columns:
            mask_installments = (
                df_clean["Down_Payment"].astype(str).str.strip() != "0"
            ) & (df_clean["Down_Payment"].astype(str).str.strip() != "")
            df_clean.loc[mask_installments, "Payment_Method"] = "Installments"

    # المرحلة الثانية من التنظيف
    df_clean = clean_data_step2(df_clean)
    df_clean = df_clean.drop(columns=["Location_4", "Location_3"])
    df_clean = df_clean.dropna()
    df_clean = df_clean.reset_index(drop=True)
    # إزالة الصفوف التي تحتوي على NaN في الأعمدة المهمة
    important_columns = ["Price", "Area", "Location"]
    for col in important_columns:
        if col in df_clean.columns:
            df_clean = df_clean[df_clean[col].notna()]

    # عرض عينة
    print("\n🔍 عينة من البيانات بعد التنظيف النهائي:")
    final_sample = df_clean[
        ["Location", "State", "Price", "Area", "Payment_Method"]
    ].head(10)
    for idx, row in final_sample.iterrows():
        print(
            f"Location: '{row['Location']}', State: '{row['State']}', "
            f"Price: {row['Price']:,.0f}, Area: {row['Area']}, Payment: {row['Payment_Method']}"
        )

    # قراءة البيانات القديمة إذا وجدت
    if os.path.exists(output_path):
        try:
            df_final = pd.read_csv(output_path)
            print(f"📁 تم العثور على بيانات موجودة: {len(df_final)} عقار")

            # دمج البيانات
            df_combined = pd.concat([df_final, df_clean], ignore_index=True)

            # إزالة التكرارات بناءً على الرابط
            if "Link" in df_combined.columns:
                initial_combined = len(df_combined)
                df_combined = df_combined.drop_duplicates(subset=["Link"], keep="last")

                df_combined = df_combined.drop(
                    columns=["Location_4", "Location_3", "Scrape_Date", "Source"],
                    errors="ignore",
                )
                df_combined = df_combined.dropna()
                df_combined = df_combined.reset_index(drop=True)
                df_combined = df_combined.astype({'Bedrooms': 'int' , 'Down_Payment': 'int' , 'Bathrooms': 'int'})
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
    print("🚀 بدء جمع بيانات العقارات من كلا الموقعين")
    print("=" * 50)
    print(f"📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # إعدادات
    propertyfinder_url = (
        "https://www.propertyfinder.eg/en/search?l=30754&c=1&fu=0&ob=mr&"
    )
    bayut_url = "https://www.bayut.eg/en/alexandria/properties-for-sale/"

    propertyfinder_pages = 40
    bayut_pages = 40
    output_path = "Final1.csv"

    # جمع البيانات من PropertyFinder
    print(f"\n📥 جاري جمع البيانات من PropertyFinder ({propertyfinder_pages} صفحات)...")
    propertyfinder_properties = scrape_all_propertyfinder_pages(
        propertyfinder_url, max_pages=propertyfinder_pages
    )
    print(f"✅ تم جمع {len(propertyfinder_properties)} عقار من PropertyFinder")

    # جمع البيانات من Bayut
    print(f"\n📥 جاري جمع البيانات من Bayut ({bayut_pages} صفحات)...")
    bayut_properties = scrape_all_bayut_pages(bayut_url, max_pages=bayut_pages)
    print(f"✅ تم جمع {len(bayut_properties)} عقار من Bayut")

    # دمج البيانات
    all_properties = propertyfinder_properties + bayut_properties

    if not all_properties:
        print("❌ لم يتم جمع أي عقارات!")
        return False

    # تحويل إلى DataFrame
    df_raw = pd.DataFrame(all_properties)
    print(f"\n📊 إجمالي العقارات المجمعة: {len(df_raw)} عقار")
    print(f"  - PropertyFinder: {len(propertyfinder_properties)} عقار")
    print(f"  - Bayut: {len(bayut_properties)} عقار")

    # معالجة وحفظ البيانات
    df_final = process_and_save_data(df_raw, output_path)

    # عرض ملخص
    print("\n" + "=" * 50)
    print("📋 ملخص العملية:")
    print("=" * 50)
    print(f"العقارات المجمعة: {len(df_raw)}")
    print(f"العقارات بعد التنظيف: {len(df_final)}")

    if not df_final.empty:
        if "Price" in df_final.columns:
            print(f"\n💰 متوسط السعر: {df_final['Price'].mean():,.0f} EGP")

        if "Payment_Method" in df_final.columns:
            print(f"\n💳 طرق الدفع:")
            payment_counts = df_final["Payment_Method"].value_counts()
            for method, count in payment_counts.items():
                print(f"  - {method}: {count}")

    print("=" * 50)
    print("✅ اكتملت عملية الجمع بنجاح!")

    # عرض إحصاءات إضافية
    if not df_final.empty and len(df_final) > 0:
        print(f"\n📈 إحصاءات إضافية:")
        print(f"  - عدد المناطق الفريدة: {df_final['Location'].nunique()}")
        if "Bedrooms" in df_final.columns:
            print(f"  - متوسط عدد الغرف: {df_final['Bedrooms'].mean():.1f}")
        if "Area" in df_final.columns:
            print(f"  - متوسط المساحة: {df_final['Area'].mean():.0f} m²")

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
