import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json

# إعداد الاتصال بجوجل شيت
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# تحميل بيانات اعتماد الخدمة من streamlit secrets
creds_dict = json.loads(st.secrets["service_account"])
CREDS = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
CLIENT = gspread.authorize(CREDS)

# فتح الشيت الرئيسي (غير الاسم حسب الحاجة)
SPREADSHEET_NAME = "company-data"

try:
    SHEET = CLIENT.open(SPREADSHEET_NAME)
except Exception as e:
    st.error(f"❌ خطأ في فتح الشيت: {e}")
    st.stop()

# تعريف الأقسام
departments = {
    "المالية": "Finance",
    "الموارد البشرية": "HR",
    "التسويق": "Marketing"
}

# إنشاء التابات
st.set_page_config(page_title="نظام الأقسام الموحد", layout="wide")
tabs = st.tabs(list(departments.keys()))

for i, (dept_name_ar, sheet_name_en) in enumerate(departments.items()):
    with tabs[i]:
        st.header(f"📂 قسم {dept_name_ar}")

        try:
            worksheet = SHEET.worksheet(sheet_name_en)
            data = worksheet.get_all_records()
            df = pd.DataFrame(data)
        except Exception as e:
            st.error(f"⚠️ لا يمكن قراءة البيانات من التاب '{sheet_name_en}': {e}")
            continue

        st.subheader("📋 البيانات الحالية")
        st.dataframe(df)

        st.markdown("---")
        st.subheader("➕ إضافة صف جديد")

        if not df.empty:
            new_row = []
            cols = df.columns.tolist()
            for col in cols:
                val = st.text_input(f"{col} ({dept_name_ar})", key=f"{sheet_name_en}_{col}")
                new_row.append(val)

            if st.button(f"إضافة إلى {dept_name_ar}", key=f"add_{sheet_name_en}"):
                try:
                    worksheet.append_row(new_row)
                    st.success("✅ تم الإضافة بنجاح!")
                except Exception as e:
                    st.error(f"❌ حدث خطأ أثناء الإضافة: {e}")
        else:
            st.info("لا توجد بيانات لعرض نموذج الإدخال.")
