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

def clean_dataframe(df):
    """
    פונקציה שמנקה את האקסל מכל הלכלוך של ההנהלה
    """
    # מוחק רווחים מיותרים בשמות העמודות
    df.columns = df.columns.str.strip()
    
    # אם יש תאים ריקים, הופך אותם ל"חופש" (אופטימיות זה חשוב)
    df = df.fillna("חופש")
    
    # מנקה רווחים מכל התאים בטבלה
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].str.strip()
            
    return df

def main():
    st.title("מערכת חילופי משבויות 🏴‍☠️")
    st.markdown("ברוך הבא למערכת שתציל לך את הסופ"ש. העלה את האקסל, ותן לאלגוריתם למצוא לך פראייר... אה, כלומר, *קולגה* שיחליף אותך.")

    # --- שלב 1: העלאת הקובץ ---
    st.info("👇 זרוק פה את האקסל/CSV המקורי. לא תמונות, אנחנו לא בימי הביניים.")
    uploaded_file = st.file_uploader("", type=['csv', 'xlsx'])
    
    if uploaded_file is None:
        st.stop() # עוצרים הכל עד שיש קובץ. אין קובץ? אין בריחה.

    # קריאת הקובץ
    try:
        if uploaded_file.name.endswith('csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
            
        df = clean_dataframe(df)
        
        with st.expander("👀 לחץ כאן כדי להציץ בסידור המלא (על אחריותך בלבד)"):
            st.dataframe(df, use_container_width=True)
            
    except Exception as e:
        st.error(f"הקובץ הזה מקולקל. מישהו נגע בו! (שגיאה: {e})")
        st.stop()

    st.divider()

    # --- שלב 2: מי אתה ומה הבעיה שלך? ---
    if 'שם' not in df.columns:
        st.error("🚨 קריסה! אין עמודה בשם 'שם' באקסל. מי עשה את הטבלה הזאת?!")
        st.stop()

    workers_list = df['שם'].unique().tolist()
    
    col1, col2 = st.columns(2)
    with col1:
        user_name = st.selectbox("מי אתה?", ["בחר שם..."] + workers_list)
    
    if user_name == "בחר שם...":
        st.stop()

    user_shifts = df[df['שם'] == user_name].iloc[0].to_dict()
    # מוציאים את המשמרות הפעילות (מסננים 'שם' ו'חופש')
    my_active_shifts = {day: shift for day, shift in user_shifts.items() 
                        if day != 'שם' and shift != 'חופש'}

    if not my_active_shifts:
        st.balloons()
        st.success("אין לך משמרות השבוע! אתה חופשי כמו ציפור! 🦅 עוף מפה ואל תסתכל אחורה.")
        st.stop()

    with col2:
        selected_day = st.selectbox("מאיזה יום אתה מנסה לברוח?", list(my_active_shifts.keys()))
    
    current_shift = my_active_shifts[selected_day]
    shift_hours = SHIFT_TYPES.get(current_shift, "שעות לא ידועות")
    
    st.warning(f"אאוצ'. אתה רשום למשמרת **{current_shift}** ביום **{selected_day}** ({shift_hours}). בוא נראה מי יכול להציל אותך.")
    st.divider()

    # --- שלב 3: מציאת הקורבנות (הלוגיקה) ---
    st.subheader("🎯 תוצאות החיפוש:")
    
    found_solution = False

    # 1. החלפה באותו יום (משמרת תמורת משמרת)
    potential_swaps_same_day = df[(df[selected_day] != 'חופש') & 
                                  (df[selected_day] != current_shift) & 
                                  (df['שם'] != user_name)]
    
    if not potential_swaps_same_day.empty:
        found_solution = True
        st.markdown("#### 🔄 החלפות 'ראש בראש' (באותו יום)")
        for _, row in potential_swaps_same_day.iterrows():
            partner = row['שם']
            partner_shift = row[selected_day]
            st.success(f"**{partner}** עובד/ת ב{partner_shift}. אולי תציע לו/ה את ה{current_shift} שלך?")

    # 2. החלפה תמורת חופש ביום אחר
    free_that_day = df[(df[selected_day] == 'חופש') & (df['שם'] != user_name)]
    
    complex_swaps = []
    for _, partner in free_that_day.iterrows():
        partner_name = partner['שם']
        partner_shifts = partner.to_dict()
        
        for day, p_shift in partner_shifts.items():
            if day in ['שם', selected_day]: continue 
            
            if day in df.columns:
                my_status_that_day = df[df['שם'] == user_name][day].values[0]
                
                # אם אני בחופש ביום שהוא עובד בו - מצאנו שידוך!
                if my_status_that_day == 'חופש' and p_shift != 'חופש':
                    complex_swaps.append((partner_name, day, p_shift))

    if complex_swaps:
        found_solution = True
        st.markdown("#### 🤝 דילים מורכבים (תן משמרת, קח משמרת)")
        for swap in complex_swaps:
            st.info(f"**{swap[0]}** בחופש ביום {selected_day}! אבל הוא עובד ביום **{swap[1]}** ({swap[2]}). הצע לו לקחת את המשמרת שלך עכשיו, ותחזיר לו ב{swap[1]}.")

    if not found_solution:
        st.error("המחשב חישב, חקר ובדק... והגיע למסקנה שנדפקת. אין אף אחד שיכול להחליף אותך. תכין הרבה קפה. ☕💀")

if __name__ == "__main__":
    main()