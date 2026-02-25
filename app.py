import streamlit as st
import pandas as pd
import urllib.parse

# הגדרת שעות המשמרות
SHIFT_TYPES = {
    "בוקר": "07:00-15:00",
    "בוקר ארוך": "07:00-19:00",
    "ערב": "14:30-23:00",
    "לילה ארוך": "19:00-07:00",
    "לילה": "22:30-07:00",
    "חופש": "חופש"
}

st.set_page_config(page_title="בורח ממשמרות - גרסת ה-VIP", page_icon="🏃‍♂️", layout="centered")

# --- הזרקת CSS ---
st.markdown("""
# --- הזרקת CSS ---
st.markdown("""
<style>
    /* הופך את כל האפליקציה מימין לשמאל */
    .stApp {
        direction: rtl;
    }
    
    /* מיישר את כל הטקסטים לימין */
    p, div, h1, h2, h3, h4, h5, h6, label, span {
        text-align: right !important;
    }
    
    /* מתקן את תיבות הבחירה (Selectbox) שייראו טוב בעברית */
    .stSelectbox div[data-baseweb="select"] {
        text-align: right;
    }
    
    /* טיפול בטבלה עצמה שלא תשתגע */
    [data-testid="stDataFrame"] {
        direction: rtl;
    }

    /* קסם המובייל: התאמות ספציפיות למסכים קטנים */
    @media (max-width: 768px) {
        .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 1rem !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
        h1 {
            font-size: 1.8rem !important;
        }
    }
</style>
""", unsafe_allow_html=True)
""", unsafe_allow_html=True)

def clean_dataframe(df):
    df.columns = df.columns.astype(str).str.strip()
    df = df.drop(columns=['אחוז משרה'], errors='ignore')
    
    HOURS_TO_NAMES = {
        "07:00-15:00": "בוקר", "7:00-15:00": "בוקר",
        "07:00-19:00": "בוקר ארוך", "7:00-19:00": "בוקר ארוך",
        "14:30-23:00": "ערב",
        "19:00-07:00": "לילה ארוך", "19:00-7:00": "לילה ארוך",
        "22:30-07:00": "לילה", "22:30-7:00": "לילה"
    }
    
    for col in df.columns:
        df[col] = df[col].astype(str).replace(r'\r|\n', '', regex=True).str.strip()
        if col != 'שם':
            df[col] = df[col].str.replace(' ', '', regex=False)
            for hours, name in HOURS_TO_NAMES.items():
                df[col] = df[col].replace(hours, name)
                
    df = df.replace(["nan", "None", "", "NaN"], "חופש")
    df = df.fillna("חופש")
    return df

def generate_whatsapp_msg(tone, my_shift, partner_shift, day, partner_name):
    """מייצר את הודעת הוואטסאפ לפי הטון הנבחר"""
    if tone == "נואש":
        return f"אחי, אני קורס פה. ארבל עשתה לנו בית ספר הלילה ואני מתחנן לשעות שינה. יש מצב שאתה לוקח לי את משמרת {my_shift} ביום {day} ואני אקח את ה{partner_shift} שלך? אני מחזיר לך מתי שרק תרצה, אני נואש."
    elif tone == "פילוסופי":
        return f"ניטשה אמר ש'מי שיש לו איזה למה שלמענו יחיה, יוכל לשאת כמעט כל איך'. אבל ה'איך' של משמרת {my_shift} ביום {day} פשוט גדול עליי כרגע. בא לך להתחלף ולקחת אותה תמורת ה{partner_shift} שלך?"
    elif tone == "איש משפחה במצוקה":
        return f"שומע {partner_name}? אני חייב לאסוף את ההורים של עדי מהשדה בדיוק על השעות של משמרת {my_shift} ביום {day}. תציל אותי מהפאדיחה ותחליף איתי על ה{partner_shift} שלך?"
    elif tone == "עסקי וקר":
        return f"היי {partner_name}. אני רשום ל{my_shift} ביום {day}, ואני רואה שאתה רשום ל{partner_shift}. מתאים לך להחליף? תעדכן כדי שאסגור את זה מול ההנהלה. תודה."
    elif tone == "שוחד":
        return f"עסקה שלא תוכל לסרב לה: אתה לוקח לי את משמרת {my_shift} ביום {day}, אני לוקח לך את ה{partner_shift} + קונה לך שווארמה עליי במשמרת הבאה. דיל?"
    elif tone == "סרקסטי":
        return f"היי {partner_name}, ראיתי שהאלגוריתם שידך בינינו. אתה עובד ב{partner_shift} ואני תקוע ב{my_shift} ביום {day}. בוא נתחלף כדי שאני לא אצטרך לראות את הפרצוף של הבוס. נו?"
    return ""

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
    my_active_shifts = {day: shift for day, shift in user_shifts.items() if day != 'שם' and shift != 'חופש'}

    if not my_active_shifts:
        st.balloons()
        st.success("אין לך משמרות השבוע! עוף לים ואל תסתכל אחורה. 🏖️")
        st.stop()

    with col2:
        selected_day = st.selectbox("מאיזה יום אתה מנסה לברוח?", list(my_active_shifts.keys()))
    
    current_shift = my_active_shifts[selected_day]
    st.warning(f"אתה רשום ל**{current_shift}** ביום **{selected_day}**. מצער מאוד.")
    
    all_possible_shifts = ["בוקר", "בוקר ארוך", "ערב", "לילה ארוך", "לילה", "חופש"]
    desired_shift = st.selectbox("ולאיזו משמרת היית מעדיף להחליף את זה?", all_possible_shifts)

    if desired_shift == current_shift:
        st.error("אתה מנסה להחליף את המשמרת שלך... לאותה משמרת בדיוק. הכל טוב בבית? 🤨")
        st.stop()

    st.divider()
    st.subheader(f"🎯 תוצאות החיפוש עבור '{desired_shift}':")
    found_solution = False
    tone_options = ["נואש", "פילוסופי", "איש משפחה במצוקה", "עסקי וקר", "שוחד", "סרקסטי"]

    if desired_shift != "חופש":
        potential_swaps = df[(df[selected_day] == desired_shift) & (df['שם'] != user_name)]
        if not potential_swaps.empty:
            found_solution = True
            st.markdown(f"#### 🔄 מצאנו אנשים שעובדים ב{desired_shift} ביום {selected_day}:")
            for _, row in potential_swaps.iterrows():
                partner = row['שם']
                
                # עיצוב התוצאה עם כפתור הוואטסאפ
                with st.container():
                    st.success(f"**{partner}** עובד/ת ב{desired_shift}. דבר איתו/ה!")
                    col_tone, col_btn = st.columns([2, 1])
                    with col_tone:
                        selected_tone = st.selectbox("איך לפנות אליו/ה?", tone_options, key=f"tone_{partner}_{selected_day}")
                    with col_btn:
                        st.write("") # מרווח קטן כדי ליישר את הכפתור
                        msg = generate_whatsapp_msg(selected_tone, current_shift, desired_shift, selected_day, partner)
                        url = f"https://wa.me/?text={urllib.parse.quote(msg)}"
                        st.link_button("שלח בוואטסאפ 💬", url, use_container_width=True)
                    st.write("---")
        else:
            st.warning(f"בדקתי. אין אף אחד שעובד ב{desired_shift} ביום {selected_day}.")

    else:
        free_that_day = df[(df[selected_day] == 'חופש') & (df['שם'] != user_name)]
        complex_swaps = []
        for _, partner in free_that_day.iterrows():
            partner_name = partner['שם']
            partner_shifts = partner.to_dict()
            for day, p_shift in partner_shifts.items():
                if day in ['שם', selected_day]: continue 
                if day in df.columns:
                    my_status_that_day = df[df['שם'] == user_name][day].values[0]
                    if my_status_that_day == 'חופש' and p_shift != 'חופש':
                        complex_swaps.append((partner_name, day, p_shift))

        if complex_swaps:
            found_solution = True
            st.markdown(f"#### 🌴 דילים מורכבים להשגת חופש ביום {selected_day}:")
            for swap in complex_swaps:
                partner_name = swap[0]
                swap_day = swap[1]
                partner_shift = swap[2]
                
                with st.container():
                    st.info(f"**{partner_name}** בחופש ב{selected_day}, אבל עובד ב{swap_day} ({partner_shift}). תציע לו את המשמרת שלך!")
                    col_tone, col_btn = st.columns([2, 1])
                    with col_tone:
                        selected_tone = st.selectbox("איך לפנות אליו/ה?", tone_options, key=f"tone_{partner_name}_{swap_day}_complex")
                    with col_btn:
                        st.write("")
                        # בונים הודעה שמותאמת לדיל המורכב (של יום אחר)
                        msg = generate_whatsapp_msg(selected_tone, current_shift, partner_shift, selected_day, partner_name)
                        # מוסיפים הבהרה להודעה על היום השני
                        msg += f" (ואני אחזיר לך ואקח את המשמרת שלך ביום {swap_day})."
                        url = f"https://wa.me/?text={urllib.parse.quote(msg)}"
                        st.link_button("שלח בוואטסאפ 💬", url, use_container_width=True)
                    st.write("---")

    if not found_solution:
        st.error("האלגוריתם סיים לחשב. אין דילים רלוונטיים. קח נשימה עמוקה ולך להכין קפה שחור. ☕💀")

if __name__ == "__main__":
    main()

