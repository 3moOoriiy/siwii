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
        if "GOOGLE_SERVICE_ACCOUNT_EMAIL" in st.secrets:
            credentials_info = {
                "type": "service_account",
                "project_id": st.secrets.get("GOOGLE_PROJECT_ID", ""),
                "private_key_id": st.secrets.get("GOOGLE_PRIVATE_KEY_ID", ""),
                "private_key": st.secrets["GOOGLE_PRIVATE_KEY"].replace('\\n', '\n'),
                "client_email": st.secrets["GOOGLE_SERVICE_ACCOUNT_EMAIL"],
                "client_id": st.secrets.get("GOOGLE_CLIENT_ID", ""),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{st.secrets['GOOGLE_SERVICE_ACCOUNT_EMAIL']}"
            }
            return credentials_info, None
        else:
            return None, "لم يتم العثور على بيانات الاعتماد في Streamlit secrets"
    except Exception as e:
        # إذا لم تكن متوفرة في secrets، استخدم متغيرات البيئة
        try:
            if os.getenv("GOOGLE_SERVICE_ACCOUNT_EMAIL"):
                credentials_info = {
                    "type": "service_account",
                    "project_id": os.getenv("GOOGLE_PROJECT_ID", ""),
                    "private_key_id": os.getenv("GOOGLE_PRIVATE_KEY_ID", ""),
                    "private_key": os.getenv("GOOGLE_PRIVATE_KEY", "").replace('\\n', '\n'),
                    "client_email": os.getenv("GOOGLE_SERVICE_ACCOUNT_EMAIL"),
                    "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{os.getenv('GOOGLE_SERVICE_ACCOUNT_EMAIL')}"
                }
                return credentials_info, None
            else:
                return None, "لم يتم العثور على بيانات الاعتماد في متغيرات البيئة"
        except Exception as env_error:
            return None, f"خطأ في قراءة متغيرات البيئة: {str(env_error)}"

def add_row_to_google_sheets(sheet_name, row_data, sheet_id):
    """إضافة صف جديد إلى Google Sheets"""
    try:
        # الحصول على بيانات الاعتماد
        credentials_info, error = get_google_credentials()
        
        if error:
            return {"error": error}
        
        if not credentials_info:
            return {"error": "لم يتم العثور على بيانات الاعتماد"}
        
        # التحقق من وجود المعلومات المطلوبة
        if not credentials_info.get("client_email") or not credentials_info.get("private_key"):
            return {"error": "بيانات الاعتماد غير مكتملة"}
        
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

def check_connection(sheet_id):
    """فحص الاتصال بـ Google Sheets"""
    try:
        credentials_info, error = get_google_credentials()
        
        if error:
            return {"error": error}
        
        if not credentials_info:
            return {"error": "لم يتم العثور على بيانات الاعتماد"}
        
        credentials = service_account.Credentials.from_service_account_info(
            credentials_info,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        
        service = build('sheets', 'v4', credentials=credentials)
        
        # جلب معلومات الجدول
        sheet_metadata = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        
        return {
            "success": True,
            "title": sheet_metadata.get('properties', {}).get('title', 'Unknown'),
            "sheets": [sheet.get('properties', {}).get('title', 'Unknown') 
                      for sheet in sheet_metadata.get('sheets', [])]
        }
        
    except Exception as e:
        return {"error": f"فشل في الاتصال: {str(e)}"}

# واجهة Streamlit
def main():
    st.title("إضافة بيانات إلى Google Sheets")
    
    # إعداد الصفحة
    st.sidebar.header("إعدادات الاتصال")
    
    # معرف الجدول
    try:
        sheet_id = st.secrets.get("GOOGLE_SHEET_ID", os.getenv("GOOGLE_SHEET_ID", ""))
    except:
        sheet_id = os.getenv("GOOGLE_SHEET_ID", "")
    
    # السماح للمستخدم بإدخال معرف الجدول يدوياً
    sheet_id_input = st.sidebar.text_input("معرف Google Sheet", value=sheet_id)
    
    if not sheet_id_input:
        st.error("يرجى إدخال معرف Google Sheet")
        st.info("يمكنك العثور على معرف الجدول في URL الخاص بـ Google Sheets")
        st.code("https://docs.google.com/spreadsheets/d/[SHEET_ID]/edit")
        st.stop()
    
    # فحص الاتصال
    if st.sidebar.button("فحص الاتصال"):
        with st.spinner("جاري فحص الاتصال..."):
            connection_result = check_connection(sheet_id_input)
        
        if "error" in connection_result:
            st.sidebar.error(f"خطأ في الاتصال: {connection_result['error']}")
        else:
            st.sidebar.success("✅ تم الاتصال بنجاح!")
            st.sidebar.info(f"اسم الجدول: {connection_result['title']}")
            st.sidebar.info(f"الأوراق المتاحة: {', '.join(connection_result['sheets'])}")
    
    # إدخال اسم الورقة
    sheet_name = st.text_input("اسم الورقة", value="Sheet1")
    
    # إدخال البيانات
    st.subheader("بيانات الصف الجديد")
    
    # إختيار طريقة الإدخال
    input_method = st.radio("طريقة إدخال البيانات:", 
                           ["نموذج بسيط", "JSON متقدم"])
    
    if input_method == "نموذج بسيط":
        # نموذج بسيط
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("الاسم")
            email = st.text_input("البريد الإلكتروني")
        
        with col2:
            phone = st.text_input("رقم الهاتف")
            notes = st.text_area("ملاحظات")
        
        row_data = {
            "name": name,
            "email": email,
            "phone": phone,
            "notes": notes
        }
        
        # إزالة الحقول الفارغة
        row_data = {k: v for k, v in row_data.items() if v}
        
    else:
        # JSON متقدم
        json_data = st.text_area("بيانات JSON", height=150, 
                                 placeholder='{\n  "name": "أحمد محمد",\n  "email": "ahmed@example.com",\n  "phone": "01234567890",\n  "notes": "ملاحظات"\n}')
        
        if json_data.strip():
            try:
                row_data = json.loads(json_data)
                st.success("✅ تم تحليل JSON بنجاح")
                st.json(row_data)
            except json.JSONDecodeError as e:
                st.error(f"خطأ في تنسيق JSON: {str(e)}")
                row_data = {}
        else:
            row_data = {}
    
    # زر الإرسال
    if st.button("إضافة البيانات", type="primary"):
        if not row_data:
            st.warning("يرجى إدخال بعض البيانات أولاً")
            return
        
        # إضافة البيانات إلى Google Sheets
        with st.spinner("جاري إضافة البيانات..."):
            result = add_row_to_google_sheets(sheet_name, row_data, sheet_id_input)
        
        if "error" in result:
            st.error(f"خطأ: {result['error']}")
            
            # اقتراحات للحل
            with st.expander("اقتراحات للحل"):
                st.write("• تأكد من أن معرف Google Sheet صحيح")
                st.write("• تأكد من أن ملف secrets.toml يحتوي على جميع المتغيرات المطلوبة")
                st.write("• تأكد من أن حساب الخدمة له صلاحية الوصول للجدول")
                st.write("• تأكد من أن اسم الورقة صحيح")
        else:
            st.success("✅ تم إضافة البيانات بنجاح!")
            st.balloons()
            with st.expander("تفاصيل العملية"):
                st.json(result)
    
    # معلومات مفيدة
    with st.expander("معلومات مفيدة"):
        st.markdown("""
        ### كيفية الحصول على معرف Google Sheet:
        1. افتح جدول Google Sheets
        2. انسخ الرابط من شريط العناوين
        3. معرف الجدول هو الجزء الطويل بين `/d/` و `/edit`
        
        ### مثال على الرابط:
        ```
        https://docs.google.com/spreadsheets/d/1A2B3C4D5E6F7G8H9I0J/edit#gid=0
        ```
        معرف الجدول هنا: `1A2B3C4D5E6F7G8H9I0J`
        """)


if __name__ == "__main__":
    main()
