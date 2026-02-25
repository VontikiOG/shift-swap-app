import streamlit as st
import pandas as pd

# הגדרת שעות המשמרות (שנדע מתי בדיוק אנחנו רוצים למות)
SHIFT_TYPES = {
    "בוקר": "07:00-15:00",
    "בוקר ארוך": "07:00-19:00",
    "ערב": "14:30-23:00",
    "לילה ארוך": "19:00-07:00",
    "לילה": "22:30-07:00",
    "חופש": "חופש"
}

st.set_page_config(page_title="בורח ממשמרות - גרסת ה-VIP", page_icon="🏃‍♂️", layout="centered")

# --- הזרקת CSS כדי להפוך את האתר לימין-לשמאל (RTL) ---
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
</style>
""", unsafe_allow_html=True)

def clean_dataframe(df):
    """
    פונקציה שמנקה את האקסל באגרסיביות מכל הלכלוך הסמוי של ההנהלה
    """
    # ניקוי שמות העמודות
    df.columns = df.columns.astype(str).str.strip()
    
    # מעבר על כל התאים בטבלה וניקוי יסודי
    for col in df.columns:
        # הופך לטקסט, מוחק ירידות שורה נסתרות, ומגלח רווחים מקצוות המילה
        df[col] = df[col].astype(str).replace(r'\r|\n', '', regex=True).str.strip()
        
    # אם היו תאים ריקים שהפכו לטקסט "nan", נהפוך אותם ל"חופש"
    df = df.replace(["nan", "None", "", "NaN"], "חופש")
    df = df.fillna("חופש")
    
    return df

def main():
    st.title("מערכת חילופי משבויות 🏴‍☠️")
    st.markdown("ברוך הבא למערכת שתציל לך את הסופ'ש. העלה את האקסל, ותן לאלגוריתם לעבוד בשבילך.")

    # --- שלב 1: העלאת הקובץ ---
    uploaded_file = st.file_uploader("👇 זרוק פה את האקסל/CSV", type=['csv', 'xlsx'])
    
    if uploaded_file is None:
        st.stop()

    try:
        if uploaded_file.name.endswith('csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
            
        df = clean_dataframe(df)
        
        with st.expander("👀 לחץ כאן כדי להציץ בסידור המלא"):
            st.dataframe(df, use_container_width=True)
            
    except Exception as e:
        st.error(f"הקובץ הזה מקולקל. מישהו נגע בו! (שגיאה: {e})")
        st.stop()

    st.divider()

    # --- שלב 2: מי אתה וממה אתה בורח? ---
    if 'שם' not in df.columns:
        st.error("🚨 קריסה! אין עמודה בשם 'שם' באקסל. נא לתקן את הקובץ.")
        st.stop()

    workers_list = df['שם'].unique().tolist()
    
    col1, col2 = st.columns(2)
    with col1:
        user_name = st.selectbox("מי אתה?", ["בחר שם..."] + workers_list)
    
    if user_name == "בחר שם...":
        st.stop()

    user_shifts = df[df['שם'] == user_name].iloc[0].to_dict()
    my_active_shifts = {day: shift for day, shift in user_shifts.items() 
                        if day != 'שם' and shift != 'חופש'}

    if not my_active_shifts:
        st.balloons()
        st.success("אין לך משמרות השבוע! עוף לים ואל תסתכל אחורה. 🏖️")
        st.stop()

    with col2:
        selected_day = st.selectbox("מאיזה יום אתה מנסה לברוח?", list(my_active_shifts.keys()))
    
    current_shift = my_active_shifts[selected_day]
    
    # --- שלב 3: מה אתה רוצה במקום? (השדרוג החדש!) ---
    st.warning(f"אתה רשום ל**{current_shift}** ביום **{selected_day}**. מצער מאוד.")
    
    all_possible_shifts = ["בוקר", "בוקר ארוך", "ערב", "לילה ארוך", "לילה", "חופש"]
    desired_shift = st.selectbox("ולאיזו משמרת היית מעדיף להחליף את זה?", all_possible_shifts)

    if desired_shift == current_shift:
        st.error("אתה מנסה להחליף את המשמרת שלך... לאותה משמרת בדיוק. הכל טוב בבית? 🤨")
        st.stop()

    st.divider()

    # --- שלב 4: מציאת הקורבנות לפי הסינון המדויק ---
    st.subheader(f"🎯 תוצאות החיפוש עבור '{desired_shift}':")
    
    found_solution = False

    # מקרה א': המשתמש רוצה משמרת אחרת באותו יום (לא חופש)
    if desired_shift != "חופש":
        # מחפשים מישהו שספציפית עובד במשמרת שהמשתמש רוצה, באותו יום
        potential_swaps = df[(df[selected_day] == desired_shift) & (df['שם'] != user_name)]
        
        if not potential_swaps.empty:
            found_solution = True
            st.markdown(f"#### 🔄 מצאנו אנשים שעובדים ב{desired_shift} ביום {selected_day}:")
            for _, row in potential_swaps.iterrows():
                partner = row['שם']
                st.success(f"**{partner}** עובד/ת ב{desired_shift}. דבר איתו/ה ותציע את ה{current_shift} שלך!")
        else:
            st.warning(f"בדקתי. אין אף אחד שעובד ב{desired_shift} ביום {selected_day}. כנראה כולם חכמים ממך או שהמשמרת ריקה.")

    # מקרה ב': המשתמש רוצה "חופש" ביום הזה
    else:
        # מחפשים מישהו שבחופש ביום הזה, ויכול לקחת את המשמרת שלנו תמורת יום עתידי שאנחנו בחופש
        free_that_day = df[(df[selected_day] == 'חופש') & (df['שם'] != user_name)]
        
        complex_swaps = []
        for _, partner in free_that_day.iterrows():
            partner_name = partner['שם']
            partner_shifts = partner.to_dict()
            
            for day, p_shift in partner_shifts.items():
                if day in ['שם', selected_day]: continue 
                
                if day in df.columns:
                    my_status_that_day = df[df['שם'] == user_name][day].values[0]
                    
                    # אם אני בחופש ביום שהוא עובד בו - בינגו!
                    if my_status_that_day == 'חופש' and p_shift != 'חופש':
                        complex_swaps.append((partner_name, day, p_shift))

        if complex_swaps:
            found_solution = True
            st.markdown(f"#### 🌴 דילים מורכבים להשגת חופש ביום {selected_day}:")
            for swap in complex_swaps:
                st.info(f"**{swap[0]}** בחופש ביום {selected_day}. הוא עובד ביום **{swap[1]}** ({swap[2]}). תציע לו את המשמרת שלך, ותחזיר לו ב{swap[1]}.")

    if not found_solution:
        st.error("האלגוריתם סיים לחשב. התוצאה: אין דילים רלוונטיים. קח נשימה עמוקה ולך להכין קפה שחור. ☕💀")

if __name__ == "__main__":
    main()

