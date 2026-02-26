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
    **v1.7 | אופטימיזציה ובאגים 🚀**
    * תיקון אלגוריתם שעות מנוחה: בודק גם קדימה (לילה -> בוקר) וגם אחורה (בוקר <- לילה).
    * אופטימיזציית Cache לטעינה מהירה של הנתונים.
    * נוספה תצוגת "השבוע שלי" בראש העמוד.

    **v1.6 | ההסבר המשולש 🔺**
    * שכתוב מלא של הסבר ההחלפה המשולשת בוואטסאפ לשיטת "תן וקח".
    * עיצוב מחדש של חלונית ההסבר: יישור מושלם לימין באמצעות HTML, ומשפט שרשרת.

    **v1.5 + v1.5.1 + v1.5.2 | Tap Only, RTL, Changelog 👆**
    * חיסלנו את המקלדת הקופצת במובייל! לחיצות בלבד.
    * הוספת כפתור ה-Changelog.
    * יישור לימין של רשימות.

    **v1.4 | חופש תמורת חופש 🏖️**
    * דילים חכמים לחופש: שומרים על מאזן המשמרות מול קולגות.

    **v1.3 | חלונות קופצים 🧼**
    * עורך ההודעות עבר לחלון קופץ אלגנטי (Pop-up).

    **v1.2 | גרסת האימפריה 👑**
    * מדד עומס, רשימת חרם (Blacklist), ודיווח יבש להנהלה.
    """)
    if st.button("סגירה", use_container_width=True):
        st.rerun()

@st.dialog("רגע לפני ששולחים... 💬")
def edit_and_send_dialog(default_msg):
    st.markdown("כאן אפשר לערוך, להוסיף סמיילי או להכניס עקיצה אישית לפני המעבר לוואטסאפ:")
    edited_msg = st.text_area("תוכן ההודעה", value=default_msg, height=150, label_visibility="collapsed")
    url = f"https://wa.me/?text={urllib.parse.quote(edited_msg)}"
    st.link_button("🚀 פתיחת וואטסאפ ושליחה", url, use_container_width=True)

# שימוש בקאשינג! הפונקציה הזו תרוץ פעם אחת בלבד ותחסוך משאבים
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
    """אלגוריתם משופר לבדיקת שעות מנוחה (קדימה ואחורה)"""
    days = [col for col in df.columns if col != 'שם']
    if day_taking not in days:
        return True
        
    idx = days.index(day_taking)
    
    # חוק 1: אם אני לוקח לילה, אסור לי בוקר ביום שאחרי
    if shift_to_take in ["לילה 🌙", "לילה ארוך 🦉"]:
        if idx + 1 < len(days):
            next_day = days[idx + 1]
            partner_next_shift = df[df['שם'] == person_taking_shift][next_day].values[0]
            if partner_next_shift in ["בוקר ☀️", "בוקר ארוך 🌤️"]:
                return False 
                
    # חוק 2: אם אני לוקח בוקר, אסור לי לילה ביום שלפני (הבאג שתוקן!)
    if shift_to_take in ["בוקר ☀️", "בוקר ארוך 🌤️"]:
        if idx - 1 >= 0:
            prev_day = days[idx - 1]
            partner_prev_shift = df[df['שם'] == person_taking_shift][prev_day].values[0]
            if partner_prev_shift in ["לילה 🌙", "לילה ארוך 🦉"]:
                return False
                
    return True

def get_workload_text(person_name, df):
    person_data = df[df['שם'] == person_name].iloc[0]
    shifts_count = sum(1 for col, val in person_data.items() if col != 'שם' and val != 'חופש 🌴')
    
    if shifts_count <= 2:
        return f"🎯 מטרה קלה! (רק {shifts_count} משמרות השבוע)"
    elif shifts_count >= 5:
        return f"⚠️ קורס/ת מעומס ({shifts_count} משמרות השבוע)"
    else:
        return f"📊 עומס רגיל ({shifts_count} משמרות)"

def generate_whatsapp_msg(tone, my_shift, partner_shift, day, partner_name):
    if tone == "נואש":
        return f"היי {partner_name}, אני קורס פה. עבר עליי לילה לבן ואין לי מושג איך אני שורד את זה. יש מצב לקחת את ה{my_shift} שלי ב{day} ואני אקח את ה{partner_shift} במקום? מבטיח להחזיר בגדול, תציל אותי."
    elif tone == "פילוסופי":
        return f"קרל מרקס אמר שהפועלים צריכים להתאחד. אז בוא נתאחד מול הסידור הזה: ה'איך' של משמרת {my_shift} ב{day} קשוח לי מדי כרגע. יש מצב להחלפה תמורת ה{partner_shift} שלך?"
    elif tone == "איש משפחה במצוקה":
        return f"היי {partner_name}, צץ אילוץ משפחתי משום מקום בדיוק על השעות של ה{my_shift} ב{day}. יש מצב להתחלף איתי על ה{partner_shift} שלך ולסגור לי את הפינה?"
    elif tone == "עסקי וקר":
        return f"היי {partner_name}. תקוע לי בסידור {my_shift} ב{day}, ולך יש {partner_shift}. מתאים להחליף? אם כן אעדכן את ההנהלה."
    elif tone == "שוחד":
        return f"עסקה מאפיונרית לפניך: ה{my_shift} שלי ב{day} עוברת אליך, ה{partner_shift} עוברת אליי, ולאפה שווארמה עליי במשמרת הבאה. דיל?"
    elif tone == "סרקסטי":
        return f"היי {partner_name}, האלגוריתם החליט שאנחנו הקורבנות של השבוע. המשמרת שלך היא {partner_shift} ושלי {my_shift} ב{day}. בואו נתחלף כדי שאני לא אאבד צלם אנוש מול הבוס. זורם?"
    return ""

def generate_freedom_swap_msg(tone, my_shift, my_day, partner_shift, partner_day, partner_name):
    explanation = f"ראיתי שיש לך חופש ב{my_day}. יש מצב שתיקח את ה{my_shift} שלי באותו יום, ובתמורה אני אקח את ה{partner_shift} שלך ב{partner_day}? ככה מאזן המשמרות נשאר אותו דבר, ופשוט יום החופש שלך יעבור ל{partner_day}!"
    
    if tone == "נואש":
        return f"היי {partner_name}, חייב את עזרתך, אני קורס. {explanation} תציל אותי."
    elif tone == "שוחד":
        return f"היי {partner_name}, דיל חופש עם פינוק: {explanation} פלוס קפה ומאפה עליי במשמרת הקרובה. סגרנו?"
    elif tone == "סרקסטי":
        return f"היי {partner_name}, בוא נתחכם קצת על הסידור עבודה: {explanation} זורם לך?"
    else:
        return f"היי {partner_name}. {explanation} מה אומר?"

def find_triangular_swap(user_name, user_shift, selected_day, person_a_name, person_a_shift, df, blacklist):
    person_bs = df[(df[selected_day] == 'חופש 🌴') & (df['שם'] != user_name) & (df['שם'] != person_a_name) & (~df['שם'].isin(blacklist))]
    
    valid_bs = []
    for _, row in person_bs.iterrows():
        b_name = row['שם']
        if check_legal_rest(b_name, user_shift, selected_day, df):
            
            b_shifts = row.to_dict()
            offerable_shifts = {}
            for d, s in b_shifts.items():
                if d not in ['שם', selected_day] and s != 'חופש 🌴':
                    a_status_that_day = df[df['שם'] == person_a_name][d].values[0]
                    if a_status_that_day == 'חופש 🌴':
                        if check_legal_rest(person_a_name, s, d, df):
                            offerable_shifts[d] = s
            
            if offerable_shifts:
                valid_bs.append((b_name, offerable_shifts))
                
    if not valid_bs:
        st.error("האלגוריתם נכנע. אין דיל משולש ריאלי שלא עובר על חוקי עבודה או התנגשויות. נסה שוב בשבוע הבא.")
        return
        
    st.markdown("##### 🦸‍♂️ רשימת המושיעים (הדיל המשולש):")
    
    for b_name, shifts in valid_bs:
        for d, s in shifts.items():
            workload_b = get_workload_text(b_name, df)
            with st.container(border=True):
                st.markdown(f"ההצעה ל{person_a_name}: משמרת **{s}** ב{d} (של {b_name})")
                st.caption(f"על המושיע/ה: {workload_b}")
                
                explanation_text = f"הנה ההצעה: אתה נותן לי את משמרת {person_a_shift} ב{selected_day}, ומקבל במקומה את משמרת {s} ב{d} של {b_name}. {b_name} סוגר לי את הפינה ולוקח את המשמרת שלי ({user_shift} ב{selected_day}), וככה כולם מסודרים!"
                default_msg = f"היי {person_a_name}. פתרתי לנו את הבעיה עם דיל משולש! {explanation_text} איך זה נשמע? תציל אותי."
                
                col_btn, col_pop, col_hr = st.columns([1,1,1])
                with col_btn:
                    if st.button("שליחה בוואטסאפ 💬", use_container_width=True, key=f"btn_tri_{person_a_name}_{b_name}_{d}"):
                        edit_and_send_dialog(default_msg)
                with col_pop:
                    with st.popover("💡 איך ההחלפה עובדת?", use_container_width=True):
                        html_explanation = f"""
                        <div dir="rtl" style="text-align: right; font-family: sans-serif; line-height: 1.6;">
                            <b>השורה התחתונה - מי עובד מתי?</b><br><br>
                            🟢 <b>אתה:</b> משמרת {person_a_shift} ב{selected_day} <i>(קיבלת מ{person_a_name})</i><br>
                            🔵 <b>{person_a_name}:</b> משמרת {s} ב{d} <i>(קיבל מ{b_name})</i><br>
                            🟡 <b>{b_name}:</b> משמרת {user_shift} ב{selected_day} <i>(קיבל ממך)</i><br><br>
                            🔄 <b>הסבר השרשרת:</b><br>
                            <b>{person_a_name}</b> יעבוד במשמרת של <b>{b_name}</b> ({s} ב{d}), שעכשיו <b>{b_name}</b> יעבוד במקום <b>{person_a_name}</b> במשמרת שלו ({person_a_shift} ב{selected_day}), ואז הוא יתחלף איתי במשמרת שלי ({user_shift} ב{selected_day}).
                        </div>
                        """
                        st.markdown(html_explanation, unsafe_allow_html=True)
                        
                with col_hr:
                    with st.popover("👔 דיווח להנהלה", use_container_width=True):
                        hr_msg = f"היי, מבקש/ת לעדכן על החלפת משמרות משולשת:\n- {user_name} יעשה את משמרת {person_a_shift} ב{selected_day} (במקום {person_a_name}).\n- {b_name} יעשה את משמרת {user_shift} ב{selected_day} (במקום {user_name}).\n- {person_a_name} יעשה את משמרת {s} ב{d} (במקום {b_name}).\n\nתודה מראש!"
                        st.markdown("להעתיק ולהדביק למנהל/ת:")
                        st.code(hr_msg, language="text")

def main():
    st.title("מערכת חילופי משמרות 🔄")
    
    col_ver, col_btn = st.columns([2, 1])
    with col_ver:
        st.caption("v1.7 | אופטימיזציה מטורפת 🚀")
    with col_btn:
        if st.button("מה התחדש?", type="tertiary", use_container_width=True):
            show_changelog()
            
    st.markdown("ברוכים הבאים למערכת שתנסה למזער את הנזק בסידור העבודה. רק להעלות את הקובץ, ולתת לאלגוריתם לשבור את הראש במקומכם.")

    st.info("👇 כאן זורקים את האקסל. המערכת תתעלם אוטומטית מכל הצבעים והקישוטים המיותרים שההנהלה שמה.")
    uploaded_file = st.file_uploader("", type=['csv', 'xlsx'])
    rows_to_skip = st.number_input("כמה שורות כותרת מיותרות יש למעלה? (מומלץ להשאיר 2)", min_value=0, max_value=15, value=2)
    
    if uploaded_file is None:
        st.stop()

    try:
        if uploaded_file.name.endswith('csv'):
            df = pd.read_csv(uploaded_file, skiprows=rows_to_skip)
        else:
            df = pd.read_excel(uploaded_file, skiprows=rows_to_skip)
            
        df = clean_dataframe(df) # קריאה לפונקציה השמורה ב-Cache
        
        with st.expander("👀 הצצה לסידור המלא (בלי צבעים עושי מיגרנה)"):
            st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"הקובץ לא תקין או שמישהו בהנהלה החליט לשנות את הפורמט. (שגיאה: {e})")
        st.stop()

    st.divider()

    if 'שם' not in df.columns:
        st.error("🚨 קריסה! אין עמודה בשם 'שם' באקסל. נא לתקן את הקובץ או לפטר את מי שיצר אותו.")
        st.stop()

    workers_list = df['שם'].unique().tolist()
    
    user_name = st.pills("מה שמך? (לחץ לבחירה):", workers_list, selection_mode="single")
    
    if not user_name: 
        st.info("👆 לחץ על השם שלך כדי להתחיל")
        st.stop()
            
    my_active_shifts = {day: shift for day, shift in days_only.items() if shift != 'חופש 🌴'}

    if not my_active_shifts:
        st.balloons()
        st.success("אין משמרות השבוע! או שפיטרו אותך, או שזכית בלוטו. עוף לים. 🏖️")
        st.stop()

    st.write("") 
    selected_day = st.pills("מאיזו משמרת בא לך לברוח?", list(my_active_shifts.keys()), selection_mode="single")
    
    if not selected_day:
        st.stop()

    current_shift = my_active_shifts[selected_day]
    st.warning(f"גזר הדין הנוכחי: משמרת **{current_shift}** ב{selected_day}.")
    
    with st.expander("🚫 רשימת החרם (לחץ כדי לסנן אנשים)"):
        blacklist = st.pills("בחר אנשים שלא יופיעו בתוצאות:", [w for w in workers_list if w != user_name], selection_mode="multi")
        if not blacklist:
            blacklist = []

    all_possible_shifts = ["בוקר ☀️", "בוקר ארוך 🌤️", "ערב 🌇", "לילה ארוך 🦉", "לילה 🌙", "חופש 🌴"]
    st.write("")
    desired_shifts = st.pills("לאיזו משמרת היית מעדיף לברוח? (אפשר כמה)", all_possible_shifts, selection_mode="multi")

    if not desired_shifts:
        st.stop() 

    if current_shift in desired_shifts:
        st.error("ניסיון יפה, אבל בחרת להחליף לאותה משמרת שאתה כבר עושה. הכל טוב בבית? 🤨")
        st.stop()

    st.divider()
    st.subheader(f"🎯 תוצאות החיפוש:")
    found_solution = False
    tone_options = ["נואש", "פילוסופי", "איש משפחה במצוקה", "עסקי וקר", "שוחד", "סרקסטי"]

    # --- חיפוש משמרות רגילות ---
    regular_shifts_wanted = [s for s in desired_shifts if s != "חופש 🌴"]
    
    if regular_shifts_wanted:
        potential_swaps = df[(df[selected_day].isin(regular_shifts_wanted)) & (df['שם'] != user_name) & (~df['שם'].isin(blacklist))]
        
        if not potential_swaps.empty:
            st.markdown(f"#### 🔄 פראיירים פוטנציאליים מאותו היום:")
            for _, row in potential_swaps.iterrows():
                partner = row['שם']
                partner_shift = row[selected_day]
                
                if not check_legal_rest(partner, current_shift, selected_day, df):
                    continue 
                
                found_solution = True
                workload_text = get_workload_text(partner, df)
                
                with st.container(border=True):
                    st.markdown(f"### 👤 {partner}")
                    st.caption(f"במשמרת {partner_shift} | {workload_text}")
                    
                    selected_tone = st.radio("באיזו גישה נתקוף?", tone_options, key=f"tone_{partner}_{selected_day}", horizontal=True)
                    
                    default_msg = generate_whatsapp_msg(selected_tone, current_shift, partner_shift, selected_day, partner)
                    
                    col_btn, col_hr = st.columns(2)
                    with col_btn:
                        if st.button("שליחה בוואטסאפ 💬", use_container_width=True, key=f"btn_send_{partner}_{selected_day}"):
                            edit_and_send_dialog(default_msg)
                    with col_hr:
                        with st.popover("👔 דיווח להנהלה", use_container_width=True):
                            hr_msg = f"היי, מבקש/ת לעדכן על החלפת משמרות ב{selected_day}:\n- {user_name} יעשה את משמרת {partner_shift}.\n- {partner} יעשה את משמרת {current_shift}."
                            st.markdown("להעתיק ולהדביק למנהל/ת:")
                            st.code(hr_msg, language="text")
                    
                    with st.expander(f"🔀 סירוב מ-{partner}? ננסה דיל משולש"):
                        find_triangular_swap(user_name, current_shift, selected_day, partner, partner_shift, df, blacklist)

    # --- חיפוש חופש חכם (חופש תמורת חופש) ---
    if "חופש 🌴" in desired_shifts:
        free_that_day = df[(df[selected_day] == 'חופש 🌴') & (df['שם'] != user_name) & (~df['שם'].isin(blacklist))]
        complex_swaps = []
        for _, partner in free_that_day.iterrows():
            partner_name = partner['שם']
            
            if not check_legal_rest(partner_name, current_shift, selected_day, df):
                continue
                
            partner_shifts = partner.to_dict()
            valid_return_shifts = []
            
            for day, p_shift in partner_shifts.items():
                if day in ['שם', selected_day]: continue 
                if day in df.columns:
                    my_status_that_day = df[df['שם'] == user_name][day].values[0]
                    if my_status_that_day == 'חופש 🌴' and p_shift != 'חופש 🌴':
                        if check_legal_rest(user_name, p_shift, day, df):
                            valid_return_shifts.append((day, p_shift))

            if valid_return_shifts:
                complex_swaps.append({
                    'partner': partner_name,
                    'options': valid_return_shifts
                })

        if complex_swaps:
            found_solution = True
            st.markdown(f"#### 🌴 דילים חכמים להשגת יום חופש ב{selected_day}:")
            st.caption("*(החלפה מאוזנת: אתה נותן משמרת, ולוקח משמרת ביום אחר במקומה)*")
            
            for swap in complex_swaps:
                partner_name = swap['partner']
                options = swap['options']
                workload_text = get_workload_text(partner_name, df)
                
                with st.container(border=True):
                    st.markdown(f"### 🌴 {partner_name}")
                    st.caption(f"חופש ב{selected_day} | {workload_text}")
                    
                    options_formatted = [f"לקחת לו את ה{s} ב{d}" for d, s in options]
                    selected_option_idx = st.radio("איזו משמרת תיקח במקום?", range(len(options_formatted)), format_func=lambda x: options_formatted[x], key=f"sel_shift_{partner_name}_{selected_day}", horizontal=True)
                    
                    selected_tone = st.radio("באיזו גישה נתקוף?", tone_options, key=f"tone_comp_{partner_name}_{selected_day}", horizontal=True)
                    
                    partner_day, partner_shift = options[selected_option_idx]
                    
                    default_msg = generate_freedom_swap_msg(selected_tone, current_shift, selected_day, partner_shift, partner_day, partner_name)
                    
                    col_btn, col_hr = st.columns(2)
                    with col_btn:
                        if st.button("שליחה בוואטסאפ 💬", use_container_width=True, key=f"btn_send_comp_{partner_name}_{selected_day}"):
                            edit_and_send_dialog(default_msg)
                    with col_hr:
                        with st.popover("👔 דיווח להנהלה", use_container_width=True):
                            hr_msg = f"היי, מבקש/ת לעדכן על החלפת משמרות להזזת יום חופש:\n- {user_name} יעשה את משמרת {partner_shift} ב{partner_day}.\n- {partner_name} יעשה את משמרת {current_shift} ב{selected_day}."
                            st.markdown("להעתיק ולהדביק למנהל/ת:")
                            st.code(hr_msg, language="text")

    if not found_solution:
        st.error("האלגוריתם ירק דם אבל אין אף פראייר פנוי השבוע (או שזה נופל להם על שעות מנוחה). קח נשימה עמוקה ולך להכין קפה שחור. ☕💀")

if __name__ == "__main__":
    main()

