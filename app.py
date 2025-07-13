import streamlit as st
import json
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

# إعداد متغيرات البيئة (يمكنك إضافتها في ملف .env أو في secrets.toml)
def get_google_credentials():
    """الحصول على بيانات الاعتماد من Streamlit secrets أو متغيرات البيئة"""
    try:
        # محاولة الحصول على البيانات من Streamlit secrets
        credentials_info = {
            "type": "service_account",
            "project_id": st.secrets["GOOGLE_PROJECT_ID"],
            "private_key_id": st.secrets["GOOGLE_PRIVATE_KEY_ID"],
            "private_key": st.secrets["GOOGLE_PRIVATE_KEY"].replace('\\n', '\n'),
            "client_email": st.secrets["GOOGLE_SERVICE_ACCOUNT_EMAIL"],
            "client_id": st.secrets["GOOGLE_CLIENT_ID"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{st.secrets['GOOGLE_SERVICE_ACCOUNT_EMAIL']}"
        }
        return credentials_info
    except:
        # إذا لم تكن متوفرة في secrets، استخدم متغيرات البيئة
        return {
            "type": "service_account",
            "project_id": os.getenv("GOOGLE_PROJECT_ID"),
            "private_key_id": os.getenv("GOOGLE_PRIVATE_KEY_ID"),
            "private_key": os.getenv("GOOGLE_PRIVATE_KEY", "").replace('\\n', '\n'),
            "client_email": os.getenv("GOOGLE_SERVICE_ACCOUNT_EMAIL"),
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{os.getenv('GOOGLE_SERVICE_ACCOUNT_EMAIL')}"
        }

def add_row_to_google_sheets(sheet_name, row_data, sheet_id):
    """إضافة صف جديد إلى Google Sheets"""
    try:
        # الحصول على بيانات الاعتماد
        credentials_info = get_google_credentials()
        
        # إنشاء كائن الاعتماد
        credentials = service_account.Credentials.from_service_account_info(
            credentials_info,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        
        # إنشاء خدمة Google Sheets
        service = build('sheets', 'v4', credentials=credentials)
        
        # جلب رؤوس الأعمدة أولاً لتحديد الترتيب
        headers_result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f'{sheet_name}!1:1'
        ).execute()
        
        headers = headers_result.get('values', [[]])[0]
        
        if not headers:
            return {"error": f"Headers not found in sheet: {sheet_name}"}
        
        # تحويل بيانات الصف إلى مصفوفة بالترتيب الصحيح للرؤوس
        values = [row_data.get(header, "") for header in headers]
        
        # إضافة الصف الجديد
        result = service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range=f'{sheet_name}!A:Z',
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body={'values': [values]}
        ).execute()
        
        return {"success": True, "updates": result.get('updates', {})}
        
    except Exception as e:
        return {"error": f"Failed to add row to Google Sheets: {str(e)}"}

# واجهة Streamlit
def main():
    st.title("إضافة بيانات إلى Google Sheets")
    
    # إعداد الصفحة
    st.sidebar.header("إعدادات الاتصال")
    
    # معرف الجدول (يمكن إضافته في secrets أو كمتغير بيئة)
    try:
        sheet_id = st.secrets.get("GOOGLE_SHEET_ID", os.getenv("GOOGLE_SHEET_ID"))
    except:
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
    
    if not sheet_id:
        st.error("يرجى إضافة معرف Google Sheet في متغيرات البيئة أو secrets")
        st.stop()
    
    # إدخال اسم الورقة
    sheet_name = st.text_input("اسم الورقة", value="Sheet1")
    
    # إدخال البيانات
    st.subheader("بيانات الصف الجديد")
    
    # يمكنك تخصيص هذا الجزء حسب احتياجاتك
    col1, col2 = st.columns(2)
    
    with col1:
        name = st.text_input("الاسم")
        email = st.text_input("البريد الإلكتروني")
    
    with col2:
        phone = st.text_input("رقم الهاتف")
        notes = st.text_area("ملاحظات")
    
    # أو يمكنك استخدام JSON editor للبيانات المعقدة
    st.subheader("أو أدخل البيانات كـ JSON")
    json_data = st.text_area("بيانات JSON", height=100, 
                             placeholder='{"name": "أحمد", "email": "ahmed@example.com"}')
    
    # زر الإرسال
    if st.button("إضافة البيانات"):
        # تحضير البيانات
        if json_data.strip():
            try:
                row_data = json.loads(json_data)
            except json.JSONDecodeError:
                st.error("خطأ في تنسيق JSON")
                return
        else:
            row_data = {
                "name": name,
                "email": email,
                "phone": phone,
                "notes": notes
            }
        
        # التحقق من وجود البيانات
        if not any(row_data.values()):
            st.warning("يرجى إدخال بعض البيانات أولاً")
            return
        
        # إضافة البيانات إلى Google Sheets
        with st.spinner("جاري إضافة البيانات..."):
            result = add_row_to_google_sheets(sheet_name, row_data, sheet_id)
        
        if "error" in result:
            st.error(f"خطأ: {result['error']}")
        else:
            st.success("تم إضافة البيانات بنجاح!")
            st.json(result)

if __name__ == "__main__":
    main()
