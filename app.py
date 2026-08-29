import streamlit as st
import pandas as pd
import urllib.parse
import os
import time
from datetime import datetime
import html
import re

# קבצי שרת ומספרי טלפון (הטלפון נשאב מהכספת, עם גיבוי זמני כדי שלא יקרוס לפני שתגדיר)
MANAGER_PHONE = st.secrets.get("MANAGER_PHONE")
DB_FILE = "schedule.csv"
WEEK_FILE = "week_name.txt"

st.set_page_config(page_title="בורח ממשמרות - גרסת ה-VIP", page_icon="🏃‍♂️", layout="centered")

# --- הזרקת CSS ---
st.markdown("""
<style>
    .stApp { direction: rtl; }
    p, div, h1, h2, h3, h4, h5, h6, label, span, li, button, input, textarea { text-align: right !important; }
    .block-container { padding-bottom: 350px !important; }
    [data-testid="stDataFrame"] { direction: rtl; }
    div[data-testid="stVerticalBlock"] div[data-testid="stVerticalBlock"] { gap: 0.5rem; }
    @media (max-width: 768px) {
        .block-container { padding-top: 1.5rem !important; padding-left: 0.5rem !important; padding-right: 0.5rem !important; }
        h1 { font-size: 1.8rem !important; }
        div.row-widget.stRadio > div { flex-direction: row; flex-wrap: wrap; }
    }
</style>
""", unsafe_allow_html=True)

# --- חלון קופץ: אזור מנהל מאובטח ---
@st.dialog("⚙️ אזור מנהל (למורשים בלבד)")
def admin_dialog():
    if "failed_attempts" not in st.session_state: st.session_state.failed_attempts = 0
    if "lockout_time" not in st.session_state: st.session_state.lockout_time = 0

    if time.time() < st.session_state.lockout_time:
        remaining = int(st.session_state.lockout_time - time.time())
        st.error(f"🚨 המערכת נעולה עקב ניסיונות מרובים. נסה שוב בעוד {remaining} שניות.")
        return

    if not st.session_state.admin_logged_in:
        st.markdown("רק מנהל המערכת מורשה להעלות סידור עבודה חדש.")
        admin_pass = st.text_input("סיסמת גישה", type="password", placeholder="🍕 הקלד סיסמה...")
        
        correct_password = st.secrets.get("ADMIN_PASSWORD", "PASSWORD_NOT_SET_IN_SECRETS")
        
        if st.button("התחבר", use_container_width=True):
            if admin_pass == correct_password and admin_pass != "PASSWORD_NOT_SET_IN_SECRETS":
                st.session_state.admin_logged_in = True
                st.session_state.failed_attempts = 0
                st.rerun()
            elif admin_pass != "":
                st.session_state.failed_attempts += 1
                if st.session_state.failed_attempts >= 3:
                    st.session_state.lockout_time = time.time() + 60
                    st.error("יותר מדי ניסיונות שגויים. המערכת ננעלה לדקה.")
                else:
                    st.error(f"סיסמה שגויה. נותרו לך עוד {3 - st.session_state.failed_attempts} ניסיונות.")
            
    if st.session_state.admin_logged_in:
        st.success("מחובר כמנהל המערכת!")
        week_name = st.text_input("מה שם השבוע? (לדוגמה: 24.03 - 30.03)", placeholder="שבוע פסח...")
        uploaded_file = st.file_uploader("העלה אקסל סידור עבודה חדש:", type=['csv', 'xlsx'])
        rows_to_skip = st.number_input("שורות כותרת לדילוג:", min_value=0, value=2)
        
        if st.button("💾 שמור סידור עבודה בשרת", type="primary", use_container_width=True):
            if uploaded_file and week_name:
                # חסימת קבצים כבדים (מעל 2MB)
                if uploaded_file.size > 2 * 1024 * 1024:
                    st.error("🚨 הקובץ גדול מדי! המקסימום המותר הוא 2MB (מניעת התקפות DOS).")
                    return

                try:
                    safe_week_name = html.escape(week_name)
                    df_temp = read_file_safely(uploaded_file, rows_to_skip)
                    
                    temp_csv = "temp_" + DB_FILE
                    temp_txt = "temp_" + WEEK_FILE
                    
                    df_temp.to_csv(temp_csv, index=False)
                    with open(temp_txt, "w", encoding="utf-8") as f:
                        f.write(safe_week_name)
                        
                    os.replace(temp_csv, DB_FILE)
                    os.replace(temp_txt, WEEK_FILE)
                    
                    st.success("הסידור נשמר בשרת בהצלחה! כל הצוות יראה אותו עכשיו.")
                    st.cache_data.clear() 
                    st.rerun()
                except Exception as e:
                    st.error(f"שגיאה בשמירת הקובץ: {e}")
            else:
                st.error("חובה להזין שם שבוע ולהעלות קובץ תקין.")
                
        if st.button("🚪 התנתק"):
            st.session_state.admin_logged_in = False
            st.rerun()

# --- חלון קופץ: יומן שינויים (Changelog) מפורט ---
@st.dialog("📜 יומן שינויים - היסטוריית הפיתוח")
def show_changelog():
    st.markdown("""
    **v2.2.0 | הפנתר 🐆**
    * **אבטחה ופרטיות:** הסתרת מספרי טלפון גלויים של מנהלים והעברתם לכספת השרת (Secrets).
    * **חסימת קריסות (DOS):** הגבלת העלאת קבצים למקסימום 2MB באזור הניהול.
    * **תיקון מטמון נצחי:** תיקון סנכרון Cache חכם שמתעדכן אוטומטית כשהקובץ משתנה.
    * **אופטימיזציית מנוע:** מעבר לחיפוש וקטורי וביטול לולאות איטיות (iterrows) בחישובי המשולשים, להאצה משמעותית של המערכת.

    **v2.1.0 | משמרות הלילה 🦉**
    * **תיקון קריטי לחוקי מנוחה:** בדיקה דו-כיוונית למוסר ולמקבל המשמרת.
    * **זיהוי שעות חכם:** תמיכה מלאה בהקלדות אקסל בעייתיות (עם רווחים ומקפים) כדי לזהות בוקר ולילה.
    * **משולש חכם:** אנשים שחסומים להחלפה ישירה מוצעים אוטומטית לדיל משולש.

    **v2.0.1 - v2.0.2 | חזרה למקורות 🧱**
    * הסרת כפיית פונטים חיצוניים למניעת באגי תצוגה במובייל, והסתמכות על פונט המערכת היציב והמהיר.

    **v2.0 | המבצר 🏰**
    * **הגנה מפריצות (Brute Force):** נעילת אזור הניהול לאחר 3 ניסיונות כניסה שגויים.
    * **אפס עומס (I/O Cache):** קריאת הנתונים מבוצעת פעם אחת בלבד ונשמרת בזיכרון השרת.
    * **חותמת זמן:** תצוגה מדויקת של "עודכן לאחרונה" מתי הועלה הסידור האחרון.
    * **כתיבה אטומית וחיטוי:** מניעת קריסות של קריאה/כתיבה במקביל וחסימת הזרקת קוד.

    **v1.9.3 | אבטחת מידע (Secrets) 🔐**
    * **הצפנת סיסמת המנהל:** הוצאת הסיסמה מקוד המקור (GitHub) והעברתה למנגנון ה-Secrets המאובטח של השרת.

    **v1.9.1 - v1.9.2 | товарищ מיכאל ⭐**
    * **חיסול תפריט הצד במובייל:** אזור המנהל עבר לחלון קופץ נקי ואלגנטי שלא שובר את המסך.
    * **דיווח ישיר:** כפתור שליחה ישירה לוואטסאפ של המנהל במכה אחת עם אימוג'י כוכב.

    **v1.9 | גרסת המנהלים 👔**
    * אזור מנהל שזוכר התחברות, סינון שמות ב-Cache, מניעת עיוורון מוצ"ש למשמרות לילה, ותמיכה בקידודי אקסל בעייתיים.

    **v1.8.2 | הסלקטור 🚷**
    * מנגנון סינון חכם למניעת שורות זבל (כמו "משמרת בוקר", "סה"כ") ברשימת העובדים.

    **v1.8 - v1.8.1 | מערכת SaaS ואזור מנהל ☁️🔒**
    * אזור מנהל מאובטח בסיסמה להעלאת קבצים.
    * תצוגת "השבוע האקטיבי" בראש העמוד ומערכת קבצים מרכזית לכלל הצוות.

    **v1.7 - v1.7.1 | מינימליזם ואופטימיזציה 🧹🚀**
    * הסרת תצוגת "השבוע שלי" למניעת עומס וחישוב שעות מנוחה דו-כיווני.

    **v1.6 | ההסבר המשולש 🔺**
    * שכתוב UX להחלפה משולשת בשיטת "תן וקח".

    **v1.4 - v1.5.2 | מהפכת ה-UI וחופש חכם 👆🏖️**
    * חיסול המקלדת הקופצת ומעבר ללחצני קפסולות. 
    * "חופש תמורת חופש" - שמירה על מאזן משמרות תקין מול ההנהלה.

    **v1.0 - v1.3 | הבסיס 🧱**
    * מדד עומס, רשימת חרם (Blacklist), וניסוחים שנונים לוואטסאפ.
    """)
    if st.button("סגירה", use_container_width=True):
        st.rerun()

@st.dialog("רגע לפני ששולחים... 💬")
def edit_and_send_dialog(default_msg):
    st.markdown("כאן אפשר לערוך לפני המעבר לוואטסאפ:")
    edited_msg = st.text_area("תוכן ההודעה", value=default_msg, height=150, label_visibility="collapsed")
    url = f"https://wa.me/?text={urllib.parse.quote(edited_msg)}"
    st.link_button("🚀 פתיחת וואטסאפ ושליחה", url, use_container_width=True)

def read_file_safely(file, skip):
    if file.name.endswith('csv'):
        for enc in ['utf-8', 'cp1255', 'iso-8859-8']:
            try:
                file.seek(0)
                return pd.read_csv(file, skiprows=skip, encoding=enc)
            except UnicodeDecodeError:
                continue
        raise ValueError("שגיאת קידוד: הקובץ חייב להיות תקין בעברית.")
    else:
        return pd.read_excel(file, skiprows=skip)

# תיקון Cache: העברת חותמת הזמן כפרמטר לפונקציה כדי שהמטמון יתנקה אוטומטית כשזה משתנה
@st.cache_data(show_spinner=False)
def load_server_data(mtime):
    last_updated = datetime.fromtimestamp(mtime).strftime("%d/%m/%Y בשעה %H:%M")
    
    with open(WEEK_FILE, "r", encoding="utf-8") as f:
        current_week_name = f.read()
        
    df_raw = pd.read_csv(DB_FILE)
    return df_raw, current_week_name, last_updated

@st.cache_data
def clean_dataframe(df):
    df.columns = df.columns.astype(str).str.strip()
    df = df.drop(columns=['אחוז משרה'], errors='ignore')
    
    for col in df.columns:
        df[col] = df[col].astype(str).replace(r'\r|\n', '', regex=True).str.strip()
        if col != 'שם':
            df[col] = df[col].str.replace(r'0?7:00\s*[-–]\s*15:00', 'בוקר ☀️', regex=True)
            df[col] = df[col].str.replace(r'0?7:00\s*[-–]\s*19:00', 'בוקר ארוך 🌤️', regex=True)
            df[col] = df[col].str.replace(r'14:30\s*[-–]\s*23:00', 'ערב 🌇', regex=True)
            df[col] = df[col].str.replace(r'19:00\s*[-–]\s*0?7:00', 'לילה ארוך 🦉', regex=True)
            df[col] = df[col].str.replace(r'22:30\s*[-–]\s*0?7:00', 'לילה 🌙', regex=True)
            
            mapping = {
                "בוקר": "בוקר ☀️", 
                "בוקר ארוך": "בוקר ארוך 🌤️",
                "ערב": "ערב 🌇", 
                "לילה ארוך": "לילה ארוך 🦉",
                "לילה": "לילה 🌙", 
                "חופש": "חופש 🌴"
            }
            for k, v in mapping.items():
                # התיקון כאן: הוספתי str(x) לפני ה-strip כדי למנוע קריסת float
                df[col] = df[col].apply(lambda x: v if str(x).strip() == k else x)
                
    df = df.replace(["nan", "None", "", "NaN"], "חופש 🌴")
    df = df.fillna("חופש 🌴")
    return df

@st.cache_data
def get_valid_workers(df):
    raw_workers_list = df['שם'].unique().tolist()
    forbidden_words = ["בוקר", "ערב", "לילה", "חופש", "משמרת", "סה\"כ", "סהכ", "הערות", "מנהל", "nan", "none"]
    workers_list = []
    for w in raw_workers_list:
        w_str = str(w).strip()
        if not w_str or w_str.lower() in ["nan", "none"]: continue
        if any(bad_word in w_str for bad_word in forbidden_words): continue
        workers_list.append(w_str)
    return workers_list

def is_night(shift):
    shift_str = str(shift)
    return any(term in shift_str for term in ["לילה", "19:00", "22:30", "🦉", "🌙"])

def is_morning(shift):
    shift_str = str(shift)
    return any(term in shift_str for term in ["בוקר", "7:00", "07:00", "☀️", "🌤️"])

def check_legal_rest(person_name, new_shift, day_taking, df):
    days = [col for col in df.columns if col != 'שם']
    if day_taking not in days: return True
    idx = days.index(day_taking)
    
    if is_night(new_shift):
        if idx + 1 < len(days):
            next_shift = df[df['שם'] == person_name][days[idx+1]].values[0]
            if is_morning(next_shift): return False 
                
    if is_morning(new_shift):
        if idx - 1 >= 0:
            prev_shift = df[df['שם'] == person_name][days[idx-1]].values[0]
            if is_night(prev_shift): return False
                
    return True

def get_workload_text(person_name, df):
    person_data = df[df['שם'] == person_name].iloc[0]
    shifts_count = sum(1 for col, val in person_data.items() if col != 'שם' and val != 'חופש 🌴')
    if shifts_count <= 2: return f"🎯 מטרה קלה! ({shifts_count} משמרות השבוע)"
    elif shifts_count >= 5: return f"⚠️ קורס/ת מעומס ({shifts_count} משמרות השבוע)"
    return f"📊 עומס רגיל ({shifts_count} משמרות)"

def generate_whatsapp_msg(tone, my_shift, partner_shift, day, partner_name):
    msgs = {
        "נואש": f"היי {partner_name}, אני קורס. יש מצב לקחת את ה{my_shift} שלי ב{day} ואני אקח את ה{partner_shift} במקום? תציל אותי.",
        "פילוסופי": f"היי {partner_name}, ה'איך' של משמרת {my_shift} ב{day} קשוח לי מדי. יש מצב להחלפה?",
        "שוחד": f"עסקה מאפיונרית: ה{my_shift} שלי ב{day} עוברת אליך, ה{partner_shift} עוברת אלי, ולאפה עלי. דיל?",
        "סרקסטי": f"היי {partner_name}, בוא נתחלף ב{day} כדי שאני לא אאבד צלם אנוש מול הבוס. זורם?",
        "עסקי וקר": f"היי {partner_name}. מעוניין להחליף את ה{my_shift} ב{day} ב{partner_shift} שלך?",
        "איש משפחה במצוקה": f"היי {partner_name}, צץ אילוץ משפחתי ב{day} על ה{my_shift}. יש מצב להתחלף?"
    }
    return msgs.get(tone, "")

def generate_freedom_swap_msg(tone, my_shift, my_day, partner_shift, partner_day, partner_name):
    exp = f"ראיתי שיש לך חופש ב{my_day}. יש מצב שתיקח את ה{my_shift} שלי באותו יום, ובתמורה אני אקח את ה{partner_shift} שלך ב{partner_day}?"
    return f"היי {partner_name}. {exp} ככה החופש שלך פשוט עוזב ל{partner_day}. זורם?"

def find_triangular_swap(user_name, user_shift, selected_day, person_a_name, person_a_shift, df, blacklist):
    person_bs = df[(df[selected_day] == 'חופש 🌴') & (df['שם'] != user_name) & (df['שם'] != person_a_name) & (~df['שם'].isin(blacklist))]
    if person_bs.empty: return
    
    user_a_row = df[df['שם'] == person_a_name].iloc[0]
    valid_bs = []
    
    for row in person_bs.to_dict('records'):
        b_name = row['שם']
        if check_legal_rest(b_name, user_shift, selected_day, df):
            offerable = {
                d: s for d, s in row.items() 
                if d not in ['שם', selected_day] 
                and s != 'חופש 🌴' 
                and user_a_row[d] == 'חופש 🌴' 
                and check_legal_rest(person_a_name, s, d, df)
            }
            if offerable: valid_bs.append((b_name, offerable))
                
    if not valid_bs: return
        
    st.markdown("##### 🦸‍♂️ רשימת המושיעים (הדיל המשולש):")
    for b_name, shifts in valid_bs:
        for d, s in shifts.items():
            with st.container(border=True):
                st.markdown(f"הצעה ל{person_a_name}: משמרת **{s}** ב{d} (של {b_name})")
                if selected_day == df.columns[-1] and user_shift in ["לילה 🌙", "לילה ארוך 🦉"]:
                    st.warning("⚠️ שימו לב: אתם מקבלים לילה ביום האחרון של הסידור. ודאו שאין לכם משמרת בוקר בשבוע החדש!")

                msg = f"היי {person_a_name}, פתרתי לנו את הבעיה! אתה נותן לי את ה{person_a_shift} ב{selected_day}, ומקבל את ה{s} ב{d} של {b_name}. {b_name} לוקח את ה{user_shift} שלי. זורם?"
                col_btn, col_pop, col_hr = st.columns([1,1,1])
                with col_btn:
                    if st.button("שליחה 💬", key=f"tri_{person_a_name}_{b_name}_{d}"): edit_and_send_dialog(msg)
                with col_pop:
                    with st.popover("💡 איך זה עובד?"):
                        st.markdown(f"""<div dir="rtl" style="text-align: right;">🟢 <b>אתה:</b> {person_a_shift} ({selected_day})<br>🔵 <b>{person_a_name}:</b> {s} ({d})<br>🟡 <b>{b_name}:</b> {user_shift} ({selected_day})</div>""", unsafe_allow_html=True)
                with col_hr:
                    hr_msg = f"היי מיכאל, מבקש/ת לעדכן על החלפת משמרות משולשת:\n- {user_name} יעשה את {person_a_shift} ב{selected_day} (במקום {person_a_name}).\n- {b_name} יעשה את {user_shift} ב{selected_day} (במקום {user_name}).\n- {person_a_name} יעשה את {s} ב{d} (במקום {b_name}).\n\nתודה מראש!"
                    hr_url = f"https://wa.me/{MANAGER_PHONE}?text={urllib.parse.quote(hr_msg)}"
                    st.link_button("שלח הודעה ל-товарищ מיכאל ⭐", hr_url, use_container_width=True)

def main():
    st.title("מערכת חילופי משמרות 🔄")
    
    if "admin_logged_in" not in st.session_state:
        st.session_state.admin_logged_in = False

    col_ver, col_btn_admin, col_btn_log = st.columns([2, 1, 1])
    with col_ver:
        st.caption("v2.2.0 | הפנתר 🐆")
    with col_btn_admin:
        if st.button("⚙️ מנהל", type="tertiary", use_container_width=True):
            admin_dialog()
    with col_btn_log:
        if st.button("מה התחדש?", type="tertiary", use_container_width=True):
            show_changelog()

    st.markdown("ברוכים הבאים למערכת שתנסה למזער את הנזק בסידור העבודה. רק לבחור את השם שלך ולתת לאלגוריתם לשבור את הראש.")

    # טעינת נתונים
    if not os.path.exists(DB_FILE) or not os.path.exists(WEEK_FILE):
        st.warning("⚠️ המנהל עדיין לא העלה סידור עבודה למערכת. לחצו על כפתור 'מנהל' למעלה כדי להעלות קובץ.")
        st.stop()

    try:
        mtime = os.path.getmtime(DB_FILE)
        df_raw, current_week_name, last_updated = load_server_data(mtime)
        
        st.info(f"📅 **כרגע מוצג סידור עבודה:** {current_week_name}\n\n*(עודכן לאחרונה: {last_updated})*")
        df = clean_dataframe(df_raw)
        with st.expander("👀 הצצה לסידור המלא (בלי צבעים עושי מיגרנה)"):
            st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"שגיאה בטעינת הקובץ: {e}")
        st.stop()

    st.divider()
    if 'שם' not in df.columns:
        st.error("🚨 קריסה! הקובץ שהועלה פגום (אין עמודה בשם 'שם'). המנהל נדרש להעלות קובץ תקין.")
        st.stop()

    workers_list = get_valid_workers(df)
    
    user_name = st.pills("מה שמך? (לחץ לבחירה):", workers_list, selection_mode="single")
    if not user_name: 
        st.info("👆 לחץ על השם שלך כדי להתחיל")
        st.stop()

    user_shifts = df[df['שם'] == user_name].iloc[0].to_dict()
    my_active_shifts = {day: shift for day, shift in user_shifts.items() if day != 'שם' and shift != 'חופש 🌴'}

    if not my_active_shifts:
        st.balloons()
        st.success("אין משמרות השבוע! עוף לים. 🏖️")
        st.stop()

    st.write("") 
    selected_day = st.pills("מאיזו משמרת בא לך לברוח?", list(my_active_shifts.keys()), selection_mode="single")
    if not selected_day:
        st.stop()

    current_shift = my_active_shifts[selected_day]
    st.warning(f"גזר הדין הנוכחי: משמרת **{current_shift}** ב{selected_day}.")
    
    with st.expander("🚫 רשימת החרם (לחץ כדי לסנן אנשים)"):
        blacklist = st.pills("בחר אנשים שלא יופיעו בתוצאות:", [w for w in workers_list if w != user_name], selection_mode="multi") or []

    all_possible_shifts = ["בוקר ☀️", "בוקר ארוך 🌤️", "ערב 🌇", "לילה ארוך 🦉", "לילה 🌙", "חופש 🌴"]
    st.write("")
    desired_shifts = st.pills("לאיזו משמרת היית מעדיף לברוח? (אפשר כמה)", all_possible_shifts, selection_mode="multi")

    if not desired_shifts:
        st.stop() 

    if current_shift in desired_shifts:
        st.error("בחרת להחליף לאותה משמרת שאתה כבר עושה. הכל טוב בבית? 🤨")
        st.stop()

    st.divider()
    st.subheader(f"🎯 תוצאות החיפוש:")
    found_solution = False
    tone_options = ["נואש", "פילוסופי", "איש משפחה במצוקה", "עסקי וקר", "שוחד", "סרקסטי"]

    regular_shifts_wanted = [s for s in desired_shifts if s != "חופש 🌴"]
    
    if regular_shifts_wanted:
        potential_swaps = df[(df[selected_day].isin(regular_shifts_wanted)) & (df['שם'] != user_name) & (~df['שם'].isin(blacklist))]
        
        if not potential_swaps.empty:
            st.markdown(f"#### 🔄 פראיירים פוטנציאליים מאותו היום:")
            for _, row in potential_swaps.iterrows():
                partner = row['שם']
                partner_shift = row[selected_day]
                
                can_partner_take_mine = check_legal_rest(partner, current_shift, selected_day, df)
                can_i_take_his = check_legal_rest(user_name, partner_shift, selected_day, df)
                
                if not can_i_take_his: continue 
                
                found_solution = True
                workload_text = get_workload_text(partner, df)
                
                if can_partner_take_mine:
                    with st.container(border=True):
                        st.markdown(f"### 👤 {partner}")
                        st.caption(f"במשמרת {partner_shift} | {workload_text}")
                        
                        if selected_day == df.columns[-1] and partner_shift in ["לילה 🌙", "לילה ארוך 🦉"]:
                            st.warning("⚠️ שימו לב: אתם לוקחים משמרת לילה ביום האחרון של הסידור. ודאו שאין לכם משמרת בוקר בשבוע החדש!")

                        selected_tone = st.radio("באיזו גישה נתקוף?", tone_options, key=f"tone_{partner}_{selected_day}", horizontal=True)
                        default_msg = generate_whatsapp_msg(selected_tone, current_shift, partner_shift, selected_day, partner)
                        
                        col_btn, col_hr = st.columns(2)
                        with col_btn:
                            if st.button("שליחה בוואטסאפ 💬", use_container_width=True, key=f"btn_send_{partner}_{selected_day}"):
                                edit_and_send_dialog(default_msg)
                        with col_hr:
                            hr_msg = f"היי מיכאל, מבקש/ת לעדכן על החלפת משמרות ב{selected_day}:\n- {user_name} יעשה את {partner_shift}.\n- {partner} יעשה את {current_shift}."
                            hr_url = f"https://wa.me/{MANAGER_PHONE}?text={urllib.parse.quote(hr_msg)}"
                            st.link_button("שלח הודעה ל-товарищ מיכאל ⭐", hr_url, use_container_width=True)
                                
                        with st.expander(f"🔀 סירוב מ-{partner}? ננסה דיל משולש"):
                            find_triangular_swap(user_name, current_shift, selected_day, partner, partner_shift, df, blacklist)
                else:
                    with st.expander(f"🔀 חסום חוקית (מנוחה) למסור ל-{partner}. ננסה דיל משולש?"):
                        find_triangular_swap(user_name, current_shift, selected_day, partner, partner_shift, df, blacklist)

    if "חופש 🌴" in desired_shifts:
        free_that_day = df[(df[selected_day] == 'חופש 🌴') & (df['שם'] != user_name) & (~df['שם'].isin(blacklist))]
        
        user_row = df[df['שם'] == user_name].iloc[0]
        complex_swaps = []
        
        for row in free_that_day.to_dict('records'):
            partner_name = row['שם']
            if not check_legal_rest(partner_name, current_shift, selected_day, df): continue
                
            valid_return_shifts = [(day, p_shift) for day, p_shift in row.items() 
                                   if day not in ['שם', selected_day] and p_shift != 'חופש 🌴' 
                                   and day in df.columns and user_row[day] == 'חופש 🌴' 
                                   and check_legal_rest(user_name, p_shift, day, df)]
            if valid_return_shifts:
                complex_swaps.append({'partner': partner_name, 'options': valid_return_shifts})

        if complex_swaps:
            found_solution = True
            st.markdown(f"#### 🌴 דילים חכמים להשגת יום חופש ב{selected_day}:")
            for swap in complex_swaps:
                partner_name = swap['partner']
                options = swap['options']
                
                with st.container(border=True):
                    st.markdown(f"### 🌴 {partner_name}")
                    st.caption(f"חופש ב{selected_day} | {get_workload_text(partner_name, df)}")
                    
                    options_formatted = [f"לקחת לו את ה{s} ב{d}" for d, s in options]
                    selected_option_idx = st.radio("איזו משמרת תיקח במקום?", range(len(options_formatted)), format_func=lambda x: options_formatted[x], key=f"sel_shift_{partner_name}_{selected_day}", horizontal=True)
                    selected_tone = st.radio("באיזו גישה נתקוף?", tone_options, key=f"tone_comp_{partner_name}_{selected_day}", horizontal=True)
                    partner_day, partner_shift = options[selected_option_idx]
                    
                    if partner_day == df.columns[-1] and partner_shift in ["לילה 🌙", "לילה ארוך 🦉"]:
                        st.warning("⚠️ שימו לב: אתם מקבלים משמרת לילה ביום האחרון של הסידור. ודאו שאין לכם בוקר בשבוע החדש!")

                    default_msg = generate_freedom_swap_msg(selected_tone, current_shift, selected_day, partner_shift, partner_day, partner_name)
                    
                    col_btn, col_hr = st.columns(2)
                    with col_btn:
                        if st.button("שליחה בוואטסאפ 💬", use_container_width=True, key=f"btn_send_comp_{partner_name}_{selected_day}"):
                            edit_and_send_dialog(default_msg)
                    with col_hr:
                        hr_msg = f"היי מיכאל, מבקש/ת לעדכן על החלפת משמרות להזזת יום חופש:\n- {user_name} יעשה את {partner_shift} ב{partner_day}.\n- {partner_name} יעשה את {current_shift} ב{selected_day}."
                        hr_url = f"https://wa.me/{MANAGER_PHONE}?text={urllib.parse.quote(hr_msg)}"
                        st.link_button("שלח הודעה ל-товарищ מיכאל ⭐", hr_url, use_container_width=True)

    if not found_solution:
        st.error("האלגוריתם ירק דם אבל אין אף פראייר פנוי השבוע (או שזה נופל על שעות מנוחה). קח נשימה עמוקה ולך להכין קפה שחור. ☕💀")

if __name__ == "__main__":
    main()
