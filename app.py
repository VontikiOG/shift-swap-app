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

# --- הזרקת CSS ---
st.markdown("""
<style>
    .stApp { direction: rtl; }
    p, div, h1, h2, h3, h4, h5, h6, label, span { text-align: right !important; }
    .stSelectbox div[data-baseweb="select"], .stMultiSelect div[data-baseweb="select"] { text-align: right; }
    [data-testid="stDataFrame"] { direction: rtl; }
    div[data-testid="stVerticalBlock"] div[data-testid="stVerticalBlock"] { gap: 0.5rem; }
    @media (max-width: 768px) {
        .block-container { padding: 1.5rem 0.5rem 1rem 0.5rem !important; }
        h1 { font-size: 1.8rem !important; }
    }
</style>
""", unsafe_allow_html=True)

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
    if shift_to_take not in ["לילה 🌙", "לילה ארוך 🦉"]:
        return True 
        
    days = [col for col in df.columns if col != 'שם']
    if day_taking in days:
        idx = days.index(day_taking)
        if idx + 1 < len(days):
            next_day = days[idx + 1]
            partner_next_shift = df[df['שם'] == person_taking_shift][next_day].values[0]
            if partner_next_shift in ["בוקר ☀️", "בוקר ארוך 🌤️"]:
                return False 
    return True

# שינינו את כל הטקסטים לניסוח חכם וניטרלי שלא מצריך זכר/נקבה
def generate_whatsapp_msg(tone, my_shift, partner_shift, day, partner_name):
    if tone == "נואש":
        return f"היי {partner_name}, אני קורס פה. הייתה לי חתיכת לילה לבן ואני חייב שעות שינה. אפשר אולי לקחת לי את משמרת {my_shift} ב{day} ואני אקח את ה{partner_shift} שלך? אני אחזיר לך מתי שרק צריך, אני נואש."
    elif tone == "פילוסופי":
        return f"ניטשה אמר ש'מי שיש לו איזה למה שלמענו יחיה, יוכל לשאת כמעט כל איך'. אבל ה'איך' של משמרת {my_shift} ב{day} פשוט גדול עליי כרגע. יש מצב להחלפה תמורת ה{partner_shift} שלך?"
    elif tone == "איש משפחה במצוקה":
        return f"היי {partner_name}, יש לי אילוץ משפחתי בלתי צפוי בדיוק על השעות של משמרת {my_shift} ב{day}. יש מצב להציל אותי ולהתחלף על ה{partner_shift} שלך?"
    elif tone == "עסקי וקר":
        return f"היי {partner_name}. אני רשום ל{my_shift} ב{day}, ויש לך {partner_shift}. מתאים להחליף? אם כן נעדכן את ההנהלה. תודה."
    elif tone == "שוחד":
        return f"עסקה שלא מסרבים לה: ה{my_shift} שלי ב{day} עוברת אליך, ה{partner_shift} עוברת אליי + מנת שווארמה עליי במשמרת הבאה. דיל?"
    elif tone == "סרקסטי":
        return f"היי {partner_name}, האלגוריתם שידך בינינו. המשמרת שלך ב{partner_shift} ואני תקוע ב{my_shift} ב{day}. בואו נתחלף כדי שאני לא אראה את הפרצוף של הבוס. זורם?"
    return ""

def find_triangular_swap(user_name, user_shift, selected_day, person_a_name, person_a_shift, df):
    """מנוע ההחלפה המשולשת 🔀"""
    person_bs = df[(df[selected_day] == 'חופש 🌴') & (df['שם'] != user_name) & (df['שם'] != person_a_name)]
    
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
        st.error("האלגוריתם לא מצא אף 'מושיע' שפנוי לקחת את המשמרת שלך ולהציע משהו ריאלי וחוקי בתמורה לסרבן.")
        return
        
    st.markdown("##### 🦸‍♂️ רשימת המושיעים (הדיל המשולש):")
    
    for b_name, shifts in valid_bs:
        for d, s in shifts.items():
            with st.container(border=True):
                st.markdown(f"**{b_name}** מציע/ה ל{person_a_name} את משמרת **{s}** ב{d}")
                
                # טקסט הסבר חלק וניטרלי לגמרי! בלי כפילות "יום" ובלי סוגריים.
                explanation_text = f"הנה הקומבינה: המשמרת שלך ב{selected_day} {person_a_shift} עוברת אליי. בתמורה, המשמרת של {b_name} ב{d} {s} עוברת אליך, ו-{b_name} לוקח את ה{user_shift} שלי. כולם יוצאים מורווחים!"
                
                msg = f"היי {person_a_name}. אני יודע שמשמרת ה{user_shift} שלי פחות הסתדרה, אבל פתרתי לנו את זה עם דיל משולש! {explanation_text} איך זה נשמע? זה ממש יציל אותי!"
                url = f"https://wa.me/?text={urllib.parse.quote(msg)}"
                
                col_btn, col_pop = st.columns(2)
                with col_btn:
                    st.link_button(f"שלח הצעת משולש ל-{person_a_name} 💬", url, use_container_width=True)
                with col_pop:
                    with st.popover("💡 איך ההחלפה עובדת?", use_container_width=True):
                        st.markdown("**ההסבר שיישלח בוואטסאפ:**")
                        st.info(explanation_text)
                        st.divider()
                        st.markdown("**השורה התחתונה:**")
                        # הצגה ברורה ונקייה של מי עובד מתי
                        st.write(f"👈 **{user_name}:** משמרת {person_a_shift} ב{selected_day}")
                        st.write(f"👈 **{b_name}:** משמרת {user_shift} ב{selected_day}")
                        st.write(f"👈 **{person_a_name}:** משמרת {s} ב{d}")

def main():
    st.title("מערכת חילופי משמרות 🔄")
    st.markdown("ברוך הבא למערכת שתציל לך את הסופ'ש. העלה את האקסל, ותן לאלגוריתם לעבוד בשבילך.")

    st.info("👇 זרוק פה את האקסל/CSV. המערכת תתעלם מהקישוטים של ההנהלה.")
    uploaded_file = st.file_uploader("", type=['csv', 'xlsx'])
    rows_to_skip = st.number_input("כמה שורות כותרת מיותרות יש למעלה שצריך לדלג עליהן? - תשאיר 2 כברירת מחדל", min_value=0, max_value=15, value=2)
    
    if uploaded_file is None:
        st.stop()

    try:
        if uploaded_file.name.endswith('csv'):
            df = pd.read_csv(uploaded_file, skiprows=rows_to_skip)
        else:
            df = pd.read_excel(uploaded_file, skiprows=rows_to_skip)
            
        df = clean_dataframe(df)
        with st.expander("👀 לחץ כאן כדי להציץ בסידור המלא"):
            st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"הקובץ הזה מקולקל. מישהו נגע בו! (שגיאה: {e})")
        st.stop()

    st.divider()

    if 'שם' not in df.columns:
        st.error("🚨 קריסה! אין עמודה בשם 'שם' באקסל. נא לתקן את הקובץ.")
        st.stop()

    workers_list = df['שם'].unique().tolist()
    
    col1, col2 = st.columns(2)
    with col1:
        user_name = st.selectbox("מי אתה?", ["בחר שם..."] + workers_list)
    if user_name == "בחר שם...": st.stop()

    user_shifts = df[df['שם'] == user_name].iloc[0].to_dict()
    my_active_shifts = {day: shift for day, shift in user_shifts.items() if day != 'שם' and shift != 'חופש 🌴'}

    if not my_active_shifts:
        st.balloons()
        st.success("אין לך משמרות השבוע! עוף לים ואל תסתכל אחורה. 🏖️")
        st.stop()

    with col2:
        selected_day = st.selectbox("מאיזה יום אתה מנסה לברוח?", list(my_active_shifts.keys()))
    
    current_shift = my_active_shifts[selected_day]
    st.warning(f"אתה רשום ל**{current_shift}** ב{selected_day}.")
    
    all_possible_shifts = ["בוקר ☀️", "בוקר ארוך 🌤️", "ערב 🌇", "לילה ארוך 🦉", "לילה 🌙", "חופש 🌴"]
    
    desired_shifts = st.multiselect("איזו משמרת היית מעדיף? (אפשר לבחור כמה אופציות)", all_possible_shifts)

    if not desired_shifts:
        st.stop() 

    if current_shift in desired_shifts:
        st.error("בחרת את המשמרת שאתה כבר רשום אליה... נא להסיר אותה מהרשימה.")
        st.stop()

    st.divider()
    st.subheader(f"🎯 תוצאות החיפוש:")
    found_solution = False
    tone_options = ["נואש", "פילוסופי", "איש משפחה במצוקה", "עסקי וקר", "שוחד", "סרקסטי"]

    # --- פיצול הלוגיקה: חיפוש משמרות רגילות ---
    regular_shifts_wanted = [s for s in desired_shifts if s != "חופש 🌴"]
    
    if regular_shifts_wanted:
        potential_swaps = df[(df[selected_day].isin(regular_shifts_wanted)) & (df['שם'] != user_name)]
        
        if not potential_swaps.empty:
            st.markdown(f"#### 🔄 דילים של החלפת משמרות (אותו יום):")
            for _, row in potential_swaps.iterrows():
                partner = row['שם']
                partner_shift = row[selected_day]
                
                if not check_legal_rest(partner, current_shift, selected_day, df):
                    continue 
                
                found_solution = True
                with st.container(border=True):
                    col_info, col_tone, col_btn = st.columns([1.5, 2, 1])
                    with col_info:
                        st.markdown(f"### 👤 {partner}")
                        st.caption(f"עובד/ת ב-{partner_shift}")
                    with col_tone:
                        selected_tone = st.selectbox("איך לפנות אליו/ה?", tone_options, key=f"tone_{partner}_{selected_day}")
                    with col_btn:
                        st.write("") 
                        msg = generate_whatsapp_msg(selected_tone, current_shift, partner_shift, selected_day, partner)
                        url = f"https://wa.me/?text={urllib.parse.quote(msg)}"
                        st.link_button("שלח בוואטסאפ 💬", url, use_container_width=True)
                    
                    with st.expander(f"🔀 {partner} סירב/ה לך? חפש דיל משולש"):
                        find_triangular_swap(user_name, current_shift, selected_day, partner, partner_shift, df)

    # --- פיצול הלוגיקה: חיפוש חופש ---
    if "חופש 🌴" in desired_shifts:
        free_that_day = df[(df[selected_day] == 'חופש 🌴') & (df['שם'] != user_name)]
        complex_swaps = []
        for _, partner in free_that_day.iterrows():
            partner_name = partner['שם']
            
            if not check_legal_rest(partner_name, current_shift, selected_day, df):
                continue
                
            partner_shifts = partner.to_dict()
            for day, p_shift in partner_shifts.items():
                if day in ['שם', selected_day]: continue 
                if day in df.columns:
                    my_status_that_day = df[df['שם'] == user_name][day].values[0]
                    if my_status_that_day == 'חופש 🌴' and p_shift != 'חופש 🌴':
                        complex_swaps.append((partner_name, day, p_shift))

        if complex_swaps:
            found_solution = True
            st.markdown(f"#### 🌴 דילים מורכבים להשגת חופש ביום {selected_day}:")
            st.caption("*(בדקתי שלמחליפים שלך לא יווצר 'לילה-בוקר' לא חוקי)*")
            for swap in complex_swaps:
                partner_name = swap[0]
                swap_day = swap[1]
                partner_shift = swap[2]
                
                with st.container(border=True):
                    col_info, col_tone, col_btn = st.columns([1.5, 2, 1])
                    with col_info:
                        st.markdown(f"### 🌴 {partner_name}")
                        st.caption(f"בחופש ב-{selected_day} | עובד/ת ב-{swap_day} ({partner_shift})")
                    with col_tone:
                        selected_tone = st.selectbox("איך לפנות אליו/ה?", tone_options, key=f"tone_{partner_name}_{swap_day}_complex")
                    with col_btn:
                        st.write("")
                        msg = generate_whatsapp_msg(selected_tone, current_shift, partner_shift, selected_day, partner_name)
                        # ניסוח ניטרלי גם פה (הסרתי "אחזיר/תחזיר")
                        msg += f" (ואני אחזיר לך משמרת ב{swap_day})."
                        url = f"https://wa.me/?text={urllib.parse.quote(msg)}"
                        st.link_button("שלח בוואטסאפ 💬", url, use_container_width=True)

    if not found_solution:
        st.error("האלגוריתם סיים לחשב. אין דילים רלוונטיים (או שזה נופל להם על שעות מנוחה). קח נשימה עמוקה ולך להכין קפה שחור. ☕💀")

if __name__ == "__main__":
    main()
