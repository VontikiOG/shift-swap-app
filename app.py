import streamlit as st
import pandas as pd
import urllib.parse

# הגדרת שעות המשמרות 
SHIFT_TYPES = {
    "בוקר ☀️": "07:00-15:00",
    "בוקר ארוך 🌤️": "07:00-19:00",
    "ערב 🌇": "14:30-23:00",
    "לילה ארוך 🦉": "19:00-07:00",
    "לילה 🌙": "22:30-07:00",
    "חופש 🌴": "חופש"
}

st.set_page_config(page_title="בורח ממשמרות - גרסת ה-VIP", page_icon="🏃‍♂️", layout="centered")

# --- הזרקת CSS מיוחדת למובייל ---
st.markdown("""
<style>
    .stApp { direction: rtl; }
    p, div, h1, h2, h3, h4, h5, h6, label, span, li { text-align: right !important; }
    
    /* כרית אוויר ענקית למטה כדי לברוח מהפרסומות של האחסון */
    .block-container { 
        padding-bottom: 350px !important; 
    }
    
    [data-testid="stDataFrame"] { direction: rtl; }
    div[data-testid="stVerticalBlock"] div[data-testid="stVerticalBlock"] { gap: 0.5rem; }
    
    @media (max-width: 768px) {
        .block-container { padding-top: 1.5rem !important; padding-left: 0.5rem !important; padding-right: 0.5rem !important; }
        h1 { font-size: 1.8rem !important; }
        div.row-widget.stRadio > div { flex-direction: row; flex-wrap: wrap; }
    }
</style>
""", unsafe_allow_html=True)

# --- חלון קופץ: יומן שינויים (Changelog) ---
@st.dialog("📜 יומן שינויים (Changelog)")
def show_changelog():
    st.markdown("""
    **v1.7.1 | מינימליזם 🧹**
    * הוסרה תצוגת "השבוע שלי" לבקשת המשתמש (צמצום עומס ויזואלי).
    * אופטימיזציית Cache נשמרה לביצועים מהירים.
    * תיקון אלגוריתם שעות מנוחה (בדיקה דו-כיוונית) נשאר פעיל.

    **v1.6 | ההסבר המשולש 🔺**
    * שכתוב מלא של הסבר ההחלפה המשולשת בוואטסאפ לשיטת "תן וקח".
    * עיצוב מחדש של חלונית ההסבר ב-HTML.

    **v1.5 | גרסת ה-Tap Only 👆**
    * חיסלנו את המקלדת הקופצת במובייל! לחיצות בלבד.

    **v1.2 - v1.4 | היסטוריית פיתוח 👑**
    * חלונות קופצים, דילים חכמים לחופש, מדד עומס ורשימת חרם.
    """)
    if st.button("סגירה", use_container_width=True):
        st.rerun()

@st.dialog("רגע לפני ששולחים... 💬")
def edit_and_send_dialog(default_msg):
    st.markdown("כאן אפשר לערוך לפני המעבר לוואטסאפ:")
    edited_msg = st.text_area("תוכן ההודעה", value=default_msg, height=150, label_visibility="collapsed")
    url = f"https://wa.me/?text={urllib.parse.quote(edited_msg)}"
    st.link_button("🚀 פתיחת וואטסאפ ושליחה", url, use_container_width=True)

@st.cache_data
def clean_dataframe(df):
    df.columns = df.columns.astype(str).str.strip()
    df = df.drop(columns=['אחוז משרה'], errors='ignore')
    
    HOURS_TO_NAMES = {
        "07:00-15:00": "בוקר ☀️", "7:00-15:00": "בוקר ☀️",
        "07:00-19:00": "בוקר ארוך 🌤️", "7:00-19:00": "בוקר ארוך 🌤️",
        "14:30-23:00": "ערב 🌇",
        "19:00-07:00": "לילה ארוך 🦉", "19:00-7:00": "לילה ארוך 🦉",
        "22:30-07:00": "לילה 🌙", "22:30-7:00": "לילה 🌙"
    }
    WORDS_TO_EMOJIS = {
        "בוקר": "בוקר ☀️", "בוקר ארוך": "בוקר ארוך 🌤️",
        "ערב": "ערב 🌇", "לילה ארוך": "לילה ארוך 🦉",
        "לילה": "לילה 🌙", "חופש": "חופש 🌴"
    }
    
    for col in df.columns:
        df[col] = df[col].astype(str).replace(r'\r|\n', '', regex=True).str.strip()
        if col != 'שם':
            df[col] = df[col].str.replace(' ', '', regex=False)
            for hours, name in HOURS_TO_NAMES.items():
                df[col] = df[col].replace(hours, name)
            df[col] = df[col].apply(lambda x: WORDS_TO_EMOJIS.get(x, x))
                
    df = df.replace(["nan", "None", "", "NaN"], "חופש 🌴")
    df = df.fillna("חופש 🌴")
    return df

def check_legal_rest(person_taking_shift, shift_to_take, day_taking, df):
    days = [col for col in df.columns if col != 'שם']
    if day_taking not in days: return True
    idx = days.index(day_taking)
    
    # בדיקה קדימה
    if shift_to_take in ["לילה 🌙", "לילה ארוך 🦉"]:
        if idx + 1 < len(days):
            next_shift = df[df['שם'] == person_taking_shift][days[idx+1]].values[0]
            if next_shift in ["בוקר ☀️", "בוקר ארוך 🌤️"]: return False 
                
    # בדיקה אחורה
    if shift_to_take in ["בוקר ☀️", "בוקר ארוך 🌤️"]:
        if idx - 1 >= 0:
            prev_shift = df[df['שם'] == person_taking_shift][days[idx-1]].values[0]
            if prev_shift in ["לילה 🌙", "לילה ארוך 🦉"]: return False
                
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
    valid_bs = []
    for _, row in person_bs.iterrows():
        b_name = row['שם']
        if check_legal_rest(b_name, user_shift, selected_day, df):
            b_shifts = row.to_dict()
            offerable = {d: s for d, s in b_shifts.items() if d not in ['שם', selected_day] and s != 'חופש 🌴' and df[df['שם'] == person_a_name][d].values[0] == 'חופש 🌴' and check_legal_rest(person_a_name, s, d, df)}
            if offerable: valid_bs.append((b_name, offerable))
                
    if not valid_bs: return
        
    st.markdown("##### 🦸‍♂️ רשימת המושיעים (הדיל המשולש):")
    for b_name, shifts in valid_bs:
        for d, s in shifts.items():
            with st.container(border=True):
                st.markdown(f"הצעה ל{person_a_name}: משמרת **{s}** ב{d} (של {b_name})")
                msg = f"היי {person_a_name}, פתרתי לנו את הבעיה! אתה נותן לי את ה{person_a_shift} ב{selected_day}, ומקבל את ה{s} ב{d} של {b_name}. {b_name} לוקח את ה{user_shift} שלי. זורם?"
                col_btn, col_pop = st.columns(2)
                with col_btn:
                    if st.button("שליחה 💬", key=f"tri_{b_name}_{d}"): edit_and_send_dialog(msg)
                with col_pop:
                    with st.popover("💡 איך זה עובד?"):
                        st.markdown(f"""<div dir="rtl" style="text-align: right;">🟢 <b>אתה:</b> {person_a_shift} ({selected_day})<br>🔵 <b>{person_a_name}:</b> {s} ({d})<br>🟡 <b>{b_name}:</b> {user_shift} ({selected_day})</div>""", unsafe_allow_html=True)

def main():
    st.title("מערכת חילופי משמרות 🔄")
    col_ver, col_btn = st.columns([2, 1])
    with col_ver: st.caption("v1.7.1 | גרסת המינימליזם 🧹")
    with col_btn: 
        if st.button("מה התחדש?", type="tertiary"): show_changelog()
            
    uploaded_file = st.file_uploader("העלה אקסל סידור עבודה:", type=['csv', 'xlsx'])
    rows_to_skip = st.number_input("שורות כותרת לדילוג:", min_value=0, value=2)
    
    if uploaded_file:
        try:
            df = clean_dataframe(pd.read_csv(uploaded_file, skiprows=rows_to_skip) if uploaded_file.name.endswith('csv') else pd.read_excel(uploaded_file, skiprows=rows_to_skip))
            workers = df['שם'].unique().tolist()
            user_name = st.pills("מה שמך?", workers, selection_mode="single")
            
            if user_name:
                user_data = df[df['שם'] == user_name].iloc[0].to_dict()
                active_shifts = {d: s for d, s in user_data.items() if d != 'שם' and s != 'חופש 🌴'}
                
                if not active_shifts:
                    st.success("אין לך משמרות השבוע! עוף לים. 🏖️")
                else:
                    day = st.pills("מאיזו משמרת בא לך לברוח?", list(active_shifts.keys()), selection_mode="single")
                    if day:
                        curr_s = active_shifts[day]
                        st.warning(f"גזר הדין: **{curr_s}** ב{day}.")
                        blacklist = st.pills("מי לסנן?", [w for w in workers if w != user_name], selection_mode="multi") or []
                        wanted = st.pills("לאיזו משמרת היית מעדיף לברוח?", ["בוקר ☀️", "בוקר ארוך 🌤️", "ערב 🌇", "לילה ארוך 🦉", "לילה 🌙", "חופש 🌴"], selection_mode="multi")
                        
                        if wanted:
                            st.divider()
                            found = False
                            tone_opts = ["נואש", "פילוסופי", "איש משפחה במצוקה", "עסקי וקר", "שוחד", "סרקסטי"]
                            
                            # חיפוש רגיל
                            reg_wanted = [s for s in wanted if s != "חופש 🌴"]
                            if reg_wanted:
                                pot = df[(df[day].isin(reg_wanted)) & (df['שם'] != user_name) & (~df['שם'].isin(blacklist))]
                                for _, row in pot.iterrows():
                                    p_name, p_s = row['שם'], row[day]
                                    if check_legal_rest(p_name, curr_s, day, df):
                                        found = True
                                        with st.container(border=True):
                                            st.markdown(f"### 👤 {p_name} ({p_s})")
                                            st.caption(get_workload_text(p_name, df))
                                            tone = st.radio("גישה:", tone_opts, key=f"t_{p_name}", horizontal=True)
                                            if st.button("שליחה בוואטסאפ 💬", key=f"b_{p_name}"):
                                                edit_and_send_dialog(generate_whatsapp_msg(tone, curr_s, p_s, day, p_name))
                                            with st.expander("🔀 ניסיון לדיל משולש"):
                                                find_triangular_swap(user_name, curr_s, day, p_name, p_s, df, blacklist)

                            # חיפוש חופש
                            if "חופש 🌴" in wanted:
                                free = df[(df[day] == 'חופש 🌴') & (df['שם'] != user_name) & (~df['שם'].isin(blacklist))]
                                for _, p in free.iterrows():
                                    p_n = p['שם']
                                    if check_legal_rest(p_n, curr_s, day, df):
                                        opts = [(d, s) for d, s in p.to_dict().items() if d not in ['שם', day] and s != 'חופש 🌴' and df[df['שם'] == user_name][d].values[0] == 'חופש 🌴' and check_legal_rest(user_name, s, d, df)]
                                        if opts:
                                            found = True
                                            with st.container(border=True):
                                                st.markdown(f"### 🌴 {p_n}")
                                                idx = st.radio("איזו משמרת תיקח לו במקום?", range(len(opts)), format_func=lambda x: f"{opts[x][1]} ב{opts[x][0]}", key=f"c_{p_n}", horizontal=True)
                                                if st.button("שליחה בוואטסאפ 💬", key=f"bc_{p_n}"):
                                                    edit_and_send_dialog(generate_freedom_swap_msg("רגיל", curr_s, day, opts[idx][1], opts[idx][0], p_n))

                            if not found: st.error("אין פראיירים פנויים כרגע. ☕")
        except Exception as e: st.error(f"שגיאה בקובץ: {e}")

if __name__ == "__main__": main()
