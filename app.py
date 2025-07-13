import streamlit as st
import json
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

# إعداد الصفحة
st.set_page_config(
    page_title="Google Sheets Manager",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

def get_google_service():
    """إنشاء خدمة Google Sheets"""
    credentials_info, error = get_google_credentials()
    
    if error:
        return None, error
    
    if not credentials_info:
        return None, "لم يتم العثور على بيانات الاعتماد"
    
    try:
        credentials = service_account.Credentials.from_service_account_info(
            credentials_info,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        
        service = build('sheets', 'v4', credentials=credentials)
        return service, None
    except Exception as e:
        return None, f"خطأ في إنشاء الخدمة: {str(e)}"

def get_available_sheets(sheet_id):
    """الحصول على قائمة بجميع الأوراق المتاحة في الجدول"""
    service, error = get_google_service()
    
    if error:
        return [], error
    
    try:
        sheet_metadata = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        sheets = []
        
        for sheet in sheet_metadata.get('sheets', []):
            sheet_properties = sheet.get('properties', {})
            sheets.append({
                'name': sheet_properties.get('title', 'Unknown'),
                'id': sheet_properties.get('sheetId', 0),
                'index': sheet_properties.get('index', 0)
            })
        
        return sheets, None
    except Exception as e:
        return [], f"خطأ في الحصول على الأوراق: {str(e)}"

def get_sheet_headers(sheet_id, sheet_name):
    """الحصول على رؤوس الأعمدة من ورقة معينة"""
    service, error = get_google_service()
    
    if error:
        return [], error
    
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f'{sheet_name}!1:1'
        ).execute()
        
        headers = result.get('values', [[]])[0]
        return headers, None
    except Exception as e:
        return [], f"خطأ في الحصول على الرؤوس: {str(e)}"

def add_row_to_sheet(sheet_id, sheet_name, row_data):
    """إضافة صف جديد إلى الورقة"""
    service, error = get_google_service()
    
    if error:
        return {"error": error}
    
    try:
        # الحصول على رؤوس الأعمدة
        headers, error = get_sheet_headers(sheet_id, sheet_name)
        
        if error:
            return {"error": error}
        
        if not headers:
            return {"error": f"لم يتم العثور على رؤوس في الورقة: {sheet_name}"}
        
        # تحويل البيانات إلى مصفوفة
        values = [row_data.get(header, "") for header in headers]
        
        # إضافة الصف
        result = service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range=f'{sheet_name}!A:Z',
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body={'values': [values]}
        ).execute()
        
        return {"success": True, "updates": result.get('updates', {})}
        
    except Exception as e:
        return {"error": f"خطأ في إضافة الصف: {str(e)}"}

def create_new_sheet(sheet_id, sheet_name):
    """إنشاء ورقة جديدة"""
    service, error = get_google_service()
    
    if error:
        return {"error": error}
    
    try:
        request_body = {
            'requests': [{
                'addSheet': {
                    'properties': {
                        'title': sheet_name
                    }
                }
            }]
        }
        
        result = service.spreadsheets().batchUpdate(
            spreadsheetId=sheet_id,
            body=request_body
        ).execute()
        
        return {"success": True, "result": result}
        
    except Exception as e:
        return {"error": f"خطأ في إنشاء الورقة: {str(e)}"}

def sidebar_config():
    """إعداد الشريط الجانبي"""
    st.sidebar.header("⚙️ إعدادات الاتصال")
    
    # معرف الجدول
    try:
        default_sheet_id = st.secrets.get("GOOGLE_SHEET_ID", os.getenv("GOOGLE_SHEET_ID", ""))
    except:
        default_sheet_id = os.getenv("GOOGLE_SHEET_ID", "")
    
    sheet_id = st.sidebar.text_input("📋 معرف Google Sheet", value=default_sheet_id)
    
    if not sheet_id:
        st.sidebar.error("يرجى إدخال معرف Google Sheet")
        return None, []
    
    # فحص الاتصال وجلب الأوراق
    if st.sidebar.button("🔍 فحص الاتصال"):
        with st.spinner("جاري فحص الاتصال..."):
            sheets, error = get_available_sheets(sheet_id)
        
        if error:
            st.sidebar.error(f"خطأ: {error}")
            return sheet_id, []
        else:
            st.sidebar.success("✅ تم الاتصال بنجاح!")
            st.session_state.available_sheets = sheets
    
    # الحصول على الأوراق المتاحة
    if 'available_sheets' not in st.session_state:
        sheets, error = get_available_sheets(sheet_id)
        if not error:
            st.session_state.available_sheets = sheets
        else:
            st.session_state.available_sheets = []
    
    # إنشاء ورقة جديدة
    st.sidebar.subheader("➕ إنشاء ورقة جديدة")
    new_sheet_name = st.sidebar.text_input("اسم الورقة الجديدة")
    
    if st.sidebar.button("إنشاء ورقة"):
        if new_sheet_name:
            with st.spinner("جاري إنشاء الورقة..."):
                result = create_new_sheet(sheet_id, new_sheet_name)
            
            if "error" in result:
                st.sidebar.error(f"خطأ: {result['error']}")
            else:
                st.sidebar.success("✅ تم إنشاء الورقة بنجاح!")
                # تحديث قائمة الأوراق
                sheets, _ = get_available_sheets(sheet_id)
                st.session_state.available_sheets = sheets
                st.rerun()
        else:
            st.sidebar.warning("يرجى إدخال اسم الورقة")
    
    return sheet_id, st.session_state.get('available_sheets', [])

def department_form(department_name, sheet_id, sheet_name):
    """نموذج إدخال بيانات لقسم معين"""
    st.subheader(f"📝 إدخال بيانات - {department_name}")
    
    # الحصول على رؤوس الأعمدة
    headers, error = get_sheet_headers(sheet_id, sheet_name)
    
    if error:
        st.error(f"خطأ في الحصول على رؤوس الأعمدة: {error}")
        return
    
    if not headers:
        st.warning(f"لم يتم العثور على رؤوس في الورقة: {sheet_name}")
        st.info("يرجى إضافة رؤوس الأعمدة في الصف الأول من الورقة")
        return
    
    # عرض رؤوس الأعمدة المتاحة
    with st.expander("📋 رؤوس الأعمدة المتاحة"):
        st.write(", ".join(headers))
    
    # نموذج إدخال البيانات
    st.write("### 📊 إدخال البيانات:")
    
    # إنشاء حقول الإدخال بناءً على الرؤوس
    row_data = {}
    
    # تقسيم الحقول على أعمدة
    cols = st.columns(2)
    
    for i, header in enumerate(headers):
        with cols[i % 2]:
            if header.lower() in ['date', 'تاريخ', 'التاريخ']:
                row_data[header] = str(st.date_input(f"📅 {header}"))
            elif header.lower() in ['notes', 'ملاحظات', 'تعليقات']:
                row_data[header] = st.text_area(f"📝 {header}")
            elif header.lower() in ['email', 'البريد الإلكتروني']:
                row_data[header] = st.text_input(f"📧 {header}")
            elif header.lower() in ['phone', 'رقم الهاتف', 'الهاتف']:
                row_data[header] = st.text_input(f"📱 {header}")
            else:
                row_data[header] = st.text_input(f"📄 {header}")
    
    # JSON إدخال متقدم
    with st.expander("🔧 إدخال JSON متقدم"):
        json_input = st.text_area(
            "أدخل البيانات كـ JSON:",
            height=150,
            placeholder=json.dumps({header: f"قيمة {header}" for header in headers[:3]}, 
                                 ensure_ascii=False, indent=2)
        )
        
        if json_input.strip():
            try:
                json_data = json.loads(json_input)
                st.success("✅ تم تحليل JSON بنجاح")
                row_data.update(json_data)
            except json.JSONDecodeError as e:
                st.error(f"خطأ في تنسيق JSON: {str(e)}")
    
    # أزرار العمليات
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("💾 حفظ البيانات", type="primary"):
            # إزالة الحقول الفارغة
            filtered_data = {k: v for k, v in row_data.items() if v}
            
            if not filtered_data:
                st.warning("يرجى إدخال بعض البيانات أولاً")
                return
            
            with st.spinner("جاري الحفظ..."):
                result = add_row_to_sheet(sheet_id, sheet_name, filtered_data)
            
            if "error" in result:
                st.error(f"خطأ: {result['error']}")
            else:
                st.success("✅ تم حفظ البيانات بنجاح!")
                st.balloons()
                
                # مسح النموذج
                st.rerun()
    
    with col2:
        if st.button("🗑️ مسح النموذج"):
            st.rerun()
    
    with col3:
        if st.button("👁️ معاينة البيانات"):
            st.json(row_data)

def main():
    st.title("📊 مدير Google Sheets")
    st.markdown("---")
    
    # إعداد الشريط الجانبي
    sheet_id, available_sheets = sidebar_config()
    
    if not sheet_id:
        st.error("يرجى إعداد معرف Google Sheet في الشريط الجانبي")
        return
    
    if not available_sheets:
        st.warning("لا توجد أوراق متاحة. يرجى فحص الاتصال أولاً.")
        return
    
    # إنشاء تبويبات للأقسام
    tabs = st.tabs([f"📁 {sheet['name']}" for sheet in available_sheets])
    
    for i, (tab, sheet) in enumerate(zip(tabs, available_sheets)):
        with tab:
            department_form(sheet['name'], sheet_id, sheet['name'])
    
    # معلومات مفيدة
    with st.expander("ℹ️ معلومات مفيدة"):
        st.markdown("""
        ### 🔧 كيفية استخدام النظام:
        1. **إعداد الاتصال**: أدخل معرف Google Sheet في الشريط الجانبي
        2. **فحص الاتصال**: تأكد من صحة الاتصال
        3. **إنشاء أوراق جديدة**: استخدم خيار "إنشاء ورقة جديدة"
        4. **إدخال البيانات**: اختر التبويب المناسب وأدخل البيانات
        
        ### 📋 نصائح:
        - تأكد من وجود رؤوس الأعمدة في الصف الأول
        - يمكنك استخدام JSON للبيانات المعقدة
        - استخدم "معاينة البيانات" قبل الحفظ
        """)

if __name__ == "__main__":
    main()
