# app.py
import streamlit as st
from datetime import datetime, timedelta
import pandas as pd

from config import COLLEGES, BRANCH_FULL_FORM, CSS_COLLEGE_SELECTOR
from utils import (
    get_valid_dates_in_range,
    find_next_valid_day_in_range,
    get_preferred_slot,
    normalize_date_to_ddmmyyyy,
    find_next_valid_day_for_electives,
)
from data_processing import read_timetable
from scheduling import (
    schedule_all_subjects_comprehensively,
    validate_capacity_constraints,
    optimize_schedule_by_filling_gaps,
    optimize_oe_subjects_after_scheduling,
    schedule_electives_globally,
)
from generation import (
    save_to_excel,
    save_verification_excel,
    generate_pdf_timetable,
    create_download_link,
)

# === PAGE CONFIG ===
st.set_page_config(page_title="Exam Timetable Generator", layout="wide")
st.markdown(CSS_COLLEGE_SELECTOR, unsafe_allow_html=True)

# === SESSION STATE INIT ===
if "base_date" not in st.session_state:
    st.session_state.base_date = datetime(2025, 4, 1)
if "end_date" not in st.session_state:
    st.session_state.end_date = datetime(2025, 5, 30)
if "capacity_slider" not in st.session_state:
    st.session_state.capacity_slider = 2000

# === SIDEBAR ===
def configure_sidebar():
    with st.sidebar:
        st.markdown("### Configuration")
        st.markdown("#### Examination Period")

        col1, col2 = st.columns(2)
        with col1:
            base_date_input = st.date_input(
                "Start date", value=datetime(2025, 4, 1), key="base_date_input"
            )
        with col2:
            end_date_input = st.date_input(
                "End date", value=datetime(2025, 5, 30), key="end_date_input"
            )

        base_date = datetime.combine(base_date_input, datetime.min.time())
        end_date = datetime.combine(end_date_input, datetime.min.time())

        if end_date <= base_date:
            st.error("End date must be after start date!")
            end_date = base_date + timedelta(days=30)
            st.warning(f"Auto-corrected to: {end_date.strftime('%Y-%m-%d')}")

        st.session_state.base_date = base_date
        st.session_state.end_date = end_date

        st.markdown("#### Capacity Configuration")
        st.slider(
            "Maximum Students Per Session",
            min_value=1000,
            max_value=3000,
            value=st.session_state.capacity_slider,
            step=100,
            key="capacity_slider",
            help="Max students in morning or afternoon session"
        )
        st.info(f"Current capacity: **{st.session_state.capacity_slider}** students")

        with st.expander("Holiday Configuration", expanded=True):
            holidays_input = st.text_area(
                "Enter holidays (one per line, DD-MM-YYYY):",
                value="06-04-2025\n14-04-2025\n18-04-2025",
                height=100
            )
            holidays = [
                datetime.strptime(h.strip(), "%d-%m-%Y").date()
                for h in holidays_input.split("\n") if h.strip()
            ]
        return holidays

# === MAIN ===
def main():
    st.title("Exam Timetable Generator")
    st.markdown("Upload your subject list and generate a conflict-free timetable.")

    uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])

    if uploaded_file:
        try:
            df = read_timetable(uploaded_file)
            if df.empty:
                st.error("Uploaded file is empty!")
                return

            # College selector
            selected_college = st.selectbox(
                "Select College", options=list(COLLEGES.keys()), key="selected_college"
            )
            selected_college_name = COLLEGES[selected_college]

            holidays = configure_sidebar()
            holidays_set = {h for h in holidays if h}

            base_date = st.session_state.base_date
            end_date = st.session_state.end_date
            MAX_STUDENTS_PER_SESSION = st.session_state.capacity_slider

            if st.button("Generate Timetable"):
                with st.spinner("Scheduling subjects..."):
                    df_scheduled = schedule_all_subjects_comprehensively(
                        df.copy(), holidays_set, base_date, end_date, MAX_STUDENTS_PER_SESSION
                    )

                    # Split by semester
                    df_dict = {}
                    for sem in df_scheduled['Semester'].unique():
                        df_dict[sem] = df_scheduled[df_scheduled['Semester'] == sem].copy()

                    # Schedule electives
                    df_ele = df_scheduled[df_scheduled['OE'].notna() & (df_scheduled['OE'].str.strip() != "")]
                    non_ele_max_date = pd.to_datetime(
                        df_scheduled[df_scheduled['OE'].isna() | (df_scheduled['OE'].str.strip() == "")]['Exam Date'],
                        format="%d-%m-%Y", errors='coerce'
                    ).max()
                    if pd.notna(non_ele_max_date):
                        df_scheduled = schedule_electives_globally(df_ele, non_ele_max_date.date(), holidays_set)

                    # Validation
                    is_valid, violations = validate_capacity_constraints(df_dict, MAX_STUDENTS_PER_SESSION)
                    if not is_valid:
                        st.warning(f"{len(violations)} capacity violations found!")

                    # Optimization
                    df_dict, _, _ = optimize_schedule_by_filling_gaps(df_dict, holidays_set, base_date, end_date)
                    df_dict, _, _ = optimize_oe_subjects_after_scheduling(df_dict, holidays_set)

                st.success("Timetable generated!")

                # === OUTPUTS ===
                col1, col2, col3 = st.columns(3)

                with col1:
                    try:
                        if df_dict:
                            excel_file = save_to_excel(df_dict, selected_college_name)
                            link = create_download_link(
                                excel_file,
                                f"Timetable_{selected_college.replace(' ', '_')}_Semester_Wise.xlsx",
                                "Excel"
                            )
                            st.markdown(link, unsafe_allow_html=True)
                        else:
                            st.warning("No data for Excel.")
                    except Exception as e:
                        st.error(f"Excel failed: {e}")

                with col2:
                    try:
                        if df_dict:
                            ver_file = save_verification_excel(df_dict, selected_college_name)
                            link = create_download_link(
                                ver_file,
                                f"VerificationVerification_Timetable_{selected_college.replace(' ', '_')}.xlsx",
                                "Verification"
                            )
                            st.markdown(link, unsafe_allow_html=True)
                        else:
                            st.warning("No data for verification.")
                    except Exception as e:
                        st.error(f"Verification failed: {e}")

                with col3:
                    try:
                        if df_dict:
                            pdf_file = generate_pdf_timetable(df_dict, selected_college_name)
                            link = create_download_link(
                                pdf_file,
                                f"Final_Timetable_{selected_college.replace(' ', '_')}.pdf",
                                "PDF"
                            )
                            st.markdown(link, unsafe_allow_html=True)
                        else:
                            st.warning("No data for PDF.")
                    except Exception as e:
                        st.error(f"PDF failed: {e}")

                # Display
                with st.expander("View Full Timetable"):
                    st.dataframe(df_scheduled.style.apply(lambda x: ['background: #f0f0f0' if (pd.notna(v) and v != "") else '' for v in x], axis=1))

        except Exception as e:
            st.error(f"Error: {e}")

if __name__ == "__main__":
    main()
