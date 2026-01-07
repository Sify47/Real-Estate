import pandas as pd
import numpy as np
import requests
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
        response = requests.get(page_url, headers=headers, timeout=15)
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
    """دالة لتنظيف البيانات المجمعة (مدمجة مع clean_data السابق)"""
    try:
        df_temp = df_clean.copy()

        # ===== تنظيف Location (من clean_data) =====
        # Ensure 'Location' exists
        if "Location" not in df_temp.columns:
            return df_temp

        # Split Location into parts and concatenate (drop original Location to avoid duplication)
        df_clean_split = (
            df_temp["Location"].str.split(",", expand=True).add_prefix("Location_")
        )
        df_temp = pd.concat(
            [df_temp.drop(columns=["Location"]), df_clean_split], axis=1
        )

        # Drop Location_2 if present (some rows may not have 3 parts)
        if "Location_2" in df_temp.columns:
            df_temp = df_temp.drop(columns=["Location_2"])

        # Rename parts to meaningful names
        if "Location_1" in df_temp.columns:
            df_temp = df_temp.rename(columns={"Location_1": "State"})
        else:
            df_temp["State"] = np.nan

        if "Location_0" in df_temp.columns:
            df_temp = df_temp.rename(columns={"Location_0": "Location"})
        else:
            df_temp["Location"] = np.nan

        # ===== تنظيف النصوص =====
        # Normalize text values safely on the df_temp dataframe
        if "State" in df_temp.columns:
            mask_state = df_temp["State"].notna()
            df_temp.loc[mask_state, "State"] = df_temp.loc[
                mask_state, "State"
            ].str.replace("Saba Pasha", "Saba Basha", case=False, regex=False)
            df_temp.loc[mask_state, "State"] = df_temp.loc[
                mask_state, "State"
            ].str.replace("Borg al-Arab", "Borg El Arab", case=False, regex=False)
            df_temp.loc[mask_state, "State"] = df_temp.loc[
                mask_state, "State"
            ].str.replace("Smoha", "Smouha", case=False, regex=False)

        if "Location" in df_temp.columns:
            mask_loc = df_temp["Location"].notna()
            df_temp.loc[mask_loc, "Location"] = df_temp.loc[
                mask_loc, "Location"
            ].str.replace("Smoha", "Smouha", case=False, regex=False)

        # ===== التعديل الجديد: إذا كانت State = "Alexandria" تغييرها لتصبح مثل Location =====
        if "State" in df_temp.columns and "Location" in df_temp.columns:
            # تنظيف المسافات الزائدة
            df_temp["State"] = df_temp["State"].str.strip()
            df_temp["Location"] = df_temp["Location"].str.strip()

            # تحديد الصفوف التي تحتوي على "Alexandria" في State
            alexandria_mask = df_temp["State"].str.contains(
                "Alexandria", case=False, na=False
            )

            # إذا كان هناك صفوف بها Alexandria في State
            if alexandria_mask.any():
                print(
                    f"📍 Found {alexandria_mask.sum()} rows with 'Alexandria' in State column"
                )
                print(
                    f"   Before change: State values: {df_temp.loc[alexandria_mask, 'State'].unique()[:5]}"
                )
                print(
                    f"   Before change: Location values: {df_temp.loc[alexandria_mask, 'Location'].unique()[:5]}"
                )

                # نسخ قيمة Location إلى State لهذه الصفوف
                df_temp.loc[alexandria_mask, "State"] = df_temp.loc[
                    alexandria_mask, "Location"
                ]

                print(
                    f"   After change: State values: {df_temp.loc[alexandria_mask, 'State'].unique()[:5]}"
                )

            # معالجة الحالة عندما تكون State فارغة ولكن Location تحتوي على اسم مدينة
            empty_state_mask = (df_temp["State"].isna()) | (df_temp["State"] == "")
            if empty_state_mask.any() and "Location" in df_temp.columns:
                # نسخ قيمة Location إلى State للصفوف التي State فارغة
                df_temp.loc[empty_state_mask, "State"] = df_temp.loc[
                    empty_state_mask, "Location"
                ]
                print(
                    f"📋 Filled {empty_state_mask.sum()} empty State values with Location"
                )

        # ===== تنظيف الأعمدة الرقمية (من clean_data مع تحسينات) =====

        # تنظيف Price
        if "Price" in df_temp.columns:
            # أولاً: إزالة الفاصلة وEGP
            df_temp["Price"] = (
                df_temp["Price"]
                .astype(str)
                .str.replace(",", "")
                .str.replace("EGP", "")
                .str.strip()
            )
            # تحويل إلى numeric
            df_temp["Price"] = pd.to_numeric(df_temp["Price"], errors="coerce")
            # حذف القيم غير الصالحة
            df_temp = df_temp[df_temp["Price"].notna()]

        # تنظيف Area
        if "Area" in df_temp.columns:
            # إزالة الفاصلة وm²
            df_temp["Area"] = (
                df_temp["Area"]
                .astype(str)
                .str.replace(",", "")
                .str.replace("m²", "")
                .str.strip()
            )
            # تحويل إلى numeric
            df_temp["Area"] = pd.to_numeric(df_temp["Area"], errors="coerce")
            # حذف القيم غير الصالحة
            df_temp = df_temp[df_temp["Area"].notna()]

        # تنظيف Bedrooms (من clean_data مع تحسينات)
        if "Bedrooms" in df_temp.columns:
            df_temp["Bedrooms"] = df_temp["Bedrooms"].astype(str)
            # Replace all instances of "+ Maid" with " " in column: 'Bedrooms'
            df_temp["Bedrooms"] = df_temp["Bedrooms"].str.replace(
                "+ Maid", " ", case=False, regex=False
            )
            # Replace all instances of "+" with "" in column: 'Bedrooms'
            df_temp["Bedrooms"] = df_temp["Bedrooms"].str.replace(
                "+", "", case=False, regex=False
            )
            # Replace all instances of "studio " with "1" in column: 'Bedrooms'
            df_temp["Bedrooms"] = df_temp["Bedrooms"].str.replace(
                "studio ", "1", case=False, regex=False
            )
            # Replace all instances of ".0" with "" in column: 'Bedrooms'
            df_temp["Bedrooms"] = df_temp["Bedrooms"].str.replace(
                ".0", "", case=False, regex=False
            )
            # استبدال 'Studio' بـ 1
            df_temp["Bedrooms"] = df_temp["Bedrooms"].str.replace(
                "Studio", "1", case=False, regex=False
            )
            # تحويل إلى numeric
            df_temp["Bedrooms"] = pd.to_numeric(df_temp["Bedrooms"], errors="coerce")
            # حذف القيم غير الصالحة
            df_temp = df_temp[df_temp["Bedrooms"].notna()]

        # تنظيف Bathrooms (من clean_data مع تحسينات)
        if "Bathrooms" in df_temp.columns:
            df_temp["Bathrooms"] = df_temp["Bathrooms"].astype(str)
            # Replace all instances of "+" with "" in column: 'Bathrooms'
            df_temp["Bathrooms"] = df_temp["Bathrooms"].str.replace(
                "+", "", case=False, regex=False
            )
            # Replace all instances of ".0" with "" in column: 'Bathrooms'
            df_temp["Bathrooms"] = df_temp["Bathrooms"].str.replace(
                ".0", "", case=False, regex=False
            )
            # تحويل إلى numeric
            df_temp["Bathrooms"] = pd.to_numeric(df_temp["Bathrooms"], errors="coerce")
            # حذف القيم غير الصالحة
            df_temp = df_temp[df_temp["Bathrooms"].notna()]

        # تنظيف Down_Payment (من clean_data مع تحسينات)
        if "Down_Payment" in df_temp.columns:
            df_temp["Down_Payment"] = df_temp["Down_Payment"].astype(str)

            # قائمة الاستبدالات من clean_data
            replacements = [
                (" EGP", ""),
                ("EGP", ""),
                ("monthly / 5 years", ""),
                ("monthly / 8 years", ""),
                ("0% Down Payment", "0"),
                ("monthly / 1.5 years", ""),
                ("monthly / 6 years", ""),
                ("monthly / 12 years", ""),
                ("monthly / 11 years", ""),
                ("monthly / 10 years", ""),
                ("monthly / 9 years", ""),
                ("monthly / 7 years", ""),
                ("monthly / 4 years", ""),
                ("monthly / 3 years", ""),
                ("monthly / 2 years", ""),
                ("monthly / 1 year", ""),
                (" 50 monthly / 1 year", "0"),
            ]

            for old, new in replacements:
                df_temp["Down_Payment"] = df_temp["Down_Payment"].str.replace(
                    old, new, case=False, regex=False
                )

            # إزالة الفاصلة
            df_temp["Down_Payment"] = df_temp["Down_Payment"].str.replace(",", "")

            # تحويل إلى numeric
            df_temp["Down_Payment"] = pd.to_numeric(
                df_temp["Down_Payment"], errors="coerce"
            )

            # ملء القيم الفارغة بصفر
            df_temp["Down_Payment"] = df_temp["Down_Payment"].fillna(0)

        # ===== حساب Price_Per_M (من clean_data) =====
        if "Price" in df_temp.columns and "Area" in df_temp.columns:
            # التأكد من عدم وجود أصفار في Area
            df_temp = df_temp[df_temp["Area"] > 0]

            # حساب Price_Per_M
            df_temp["Price_Per_M"] = df_temp["Price"] / df_temp["Area"]

            # Round column 'Price_Per_M' (Number of decimals: 2)
            df_temp["Price_Per_M"] = df_temp["Price_Per_M"].round(2)

        # ===== إضافة Payment_Method (من clean_scraped_data السابق) =====
        if "Down_Payment" in df_temp.columns:
            df_temp["Payment_Method"] = "Cash"
            if not df_temp.empty:
                df_temp.loc[df_temp["Down_Payment"] > 0, "Payment_Method"] = (
                    "Installments"
                )

        # ===== تنظيف إضافي وحذف الصفوف الفارغة =====
        # حذف الصفوف التي تفتقد للبيانات الأساسية
        required_columns = ["Title", "Price", "Area"]
        available_required = [col for col in required_columns if col in df_temp.columns]

        if available_required:
            df_temp = df_temp.dropna(subset=available_required)

        # إزالة التكرارات البسيطة
        duplicate_cols = ["Title", "Price", "Location", "Area"]
        available_duplicate = [col for col in duplicate_cols if col in df_temp.columns]

        if len(available_duplicate) >= 2:
            df_temp = df_temp.drop_duplicates(subset=available_duplicate, keep="first")

        # إعادة تعيين الفهرس
        df_temp = df_temp.reset_index(drop=True)

        # تحويل أنواع البيانات النهائية
        if "Bedrooms" in df_temp.columns:
            try:
                df_temp["Bedrooms"] = df_temp["Bedrooms"].astype("int8")
            except:
                pass

        if "Bathrooms" in df_temp.columns:
            try:
                df_temp["Bathrooms"] = df_temp["Bathrooms"].astype("int8")
            except:
                pass

        if "Down_Payment" in df_temp.columns:
            try:
                df_temp["Down_Payment"] = df_temp["Down_Payment"].astype("int64")
            except:
                pass

        print(f"✅ Data cleaning completed. Final shape: {df_temp.shape}")
        print(f"   Columns: {list(df_temp.columns)}")
        print(
            f"   Unique State values: {df_temp['State'].unique()[:10] if 'State' in df_temp.columns else 'N/A'}"
        )

        return df_temp

    except Exception as e:
        print(f"❌ Error in cleaning data: {e}")
        import traceback

        traceback.print_exc()
        return df_clean


def intelligent_deduplicate(new_df, old_df):
    """إزالة تكرارات ذكية تحافظ على البيانات القديمة"""

    print(f"\n🔍 Starting intelligent deduplication...")
    print(f"   New data: {len(new_df)} properties")
    print(f"   Old data: {len(old_df)} properties")

    # إذا كان الـ old_df فارغاً، ارجع الـ new_df كما هو
    if old_df.empty:
        print("   No old data to compare with")
        return new_df

    # 1. إنشاء مفتاح فريد لكل عقار
    def create_key(row):
        # استخدام عنوان ولقطة وسعر لإنشاء مفتاح
        title = (
            str(row["Title"]).strip().lower()
            if "Title" in row and pd.notna(row["Title"])
            else ""
        )
        location = (
            str(row["Location"]).strip().lower()
            if "Location" in row and pd.notna(row["Location"])
            else ""
        )
        price = str(row["Price"]) if "Price" in row and pd.notna(row["Price"]) else ""

        # أخذ أول 50 حرف من العنوان والموقع
        title_key = title[:50]
        location_key = location[:30]

        return f"{title_key}_{location_key}_{price}"

    # 2. إنشاء مفاتيح للبيانات القديمة والجديدة
    print("   Creating unique keys...")
    old_df = old_df.copy()
    new_df = new_df.copy()

    old_df["_key"] = old_df.apply(create_key, axis=1)
    new_df["_key"] = new_df.apply(create_key, axis=1)

    # 3. العثور على التكرارات
    duplicate_keys = set(new_df["_key"]).intersection(set(old_df["_key"]))

    print(f"   Found {len(duplicate_keys)} potential duplicates")

    if duplicate_keys:
        # 4. تصفية التكرارات من البيانات الجديدة
        new_df_filtered = new_df[~new_df["_key"].isin(duplicate_keys)]

        # 5. إضافة التكرارات الجديدة فقط إذا كانت مختلفة بشكل كبير
        kept_duplicates = 0
        for key in duplicate_keys:
            old_row = old_df[old_df["_key"] == key].iloc[0]
            new_row = new_df[new_df["_key"] == key].iloc[0]

            # تحقق إذا كان هناك فرق كبير في السعر (>10%)
            old_price = (
                old_row["Price"]
                if "Price" in old_row and pd.notna(old_row["Price"])
                else 0
            )
            new_price = (
                new_row["Price"]
                if "Price" in new_row and pd.notna(new_row["Price"])
                else 0
            )

            if old_price > 0 and new_price > 0:
                price_diff = abs((new_price - old_price) / old_price)

                # إذا كان الفرق في السعر أكثر من 10%، اعتبره عقاراً جديداً
                if price_diff > 0.1:
                    new_df_filtered = pd.concat(
                        [new_df_filtered, new_df[new_df["_key"] == key]],
                        ignore_index=True,
                    )
                    kept_duplicates += 1

        print(f"   Kept {kept_duplicates} duplicates with significant price changes")

        # إزالة العمود المؤقت
        new_df_filtered = new_df_filtered.drop(columns=["_key"])
    else:
        new_df_filtered = new_df.drop(columns=["_key"])

    print(f"   Final new data after deduplication: {len(new_df_filtered)} properties")

    return new_df_filtered

def main():
    print("=" * 60)
    print("🚀 Starting intelligent real estate scraping...")
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # جمع البيانات
    base_url = "https://www.bayut.eg/en/alexandria/properties-for-sale/"
    all_properties = []
    
    # جمع من صفحتين فقط لتجنب التحميل الزائد
    for page_num in range(1, 3):
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
        print(f"\n📊 Total NEW properties collected: {len(df_scraped)}")
        
        # تنظيف البيانات
        df_cleaned = clean_scraped_data(df_scraped)
        
        if not df_cleaned.empty:
            # قراءة البيانات القديمة
            if os.path.exists('Final1.csv'):
                try:
                    existing_df = pd.read_csv('Final1.csv')
                    print(f"📁 Found existing Final1.csv with {len(existing_df)} properties")
                    
                    # استخدام إزالة التكرارات الذكية
                    df_unique_new = intelligent_deduplicate(df_cleaned, existing_df)
                    
                    # دمج البيانات القديمة مع الجديدة الفريدة فقط
                    combined_df = pd.concat([existing_df, df_unique_new], ignore_index=True)
                    
                    # إزالة التكرارات النهائية (باستخدام معايير أكثر تحفظاً)
                    combined_df = combined_df.drop_duplicates(
                        subset=['Title', 'Location', 'Price', 'PropertyType', 'Bedrooms'], 
                        keep='first'  # احتفظ بالسجلات القديمة
                    )
                    
                    new_properties_added = len(combined_df) - len(existing_df)
                    print(f"🔄 After merging: {len(combined_df)} total properties")
                    print(f"➕ New properties added: {new_properties_added}")
                    
                    # إذا كان هناك نقص في البيانات، لا تحفظ
                    if new_properties_added < -10:  # إذا فقدنا أكثر من 10 عقار
                        print(f"⚠️ WARNING: Data loss detected! Keeping old file.")
                        combined_df = existing_df  # استعادة البيانات القديمة
                        new_properties_added = 0
                    
                    # حفظ البيانات
                    combined_df.to_csv('Final1.csv', index=False, encoding='utf-8')
                    print(f"💾 Saved {len(combined_df)} properties to Final1.csv")
                    
                    # حفظ metadata
                    metadata = f"""Last scraped: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
New properties collected: {len(df_cleaned)}
New properties added: {new_properties_added}
Total properties: {len(combined_df)}
Pages scraped: {min(page_num, 2)}
Status: Success"""
                    
                    with open('scraping_metadata.txt', 'w') as f:
                        f.write(metadata)
                    
                    print("\n" + "=" * 60)
                    print("✅ Scraping completed successfully!")
                    print(f"📈 Data summary:")
                    print(f"   - Old data: {len(existing_df)} properties")
                    print(f"   - New data: {len(df_cleaned)} properties")
                    print(f"   - Unique new: {len(df_unique_new)} properties")
                    print(f"   - Total now: {len(combined_df)} properties")
                    print(f"   - Net change: {new_properties_added} properties")
                    print("=" * 60)
                    
                    return True
                    
                except Exception as e:
                    print(f"❌ Error processing files: {e}")
                    import traceback
                    traceback.print_exc()
                    return False
            else:
                # إذا لم يوجد الملف، احفظ البيانات الجديدة
                df_cleaned.to_csv('Final1.csv', index=False, encoding='utf-8')
                print(f"💾 Created Final1.csv with {len(df_cleaned)} properties")
                
                metadata = f"""Last scraped: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
New properties: {len(df_cleaned)}
Total properties: {len(df_cleaned)}
Status: First run - file created"""
                
                with open('scraping_metadata.txt', 'w') as f:
                    f.write(metadata)
                
                return True
        else:
            print("⚠️ No valid data after cleaning")
            return False
    else:
        print("❌ No properties collected")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
