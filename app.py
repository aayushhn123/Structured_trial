import streamlit as st
import pandas as pd
import io
import os
from datetime import datetime, timedelta
from config import COLLEGES, BRANCH_FULL_FORM, CSS_COLLEGE_SELECTOR, CSS_MAIN_APP
from data_processing import read_timetable
from scheduling import (
    schedule_all_subjects_comprehensively,
    validate_capacity_constraints,
    optimize_schedule_by_filling_gaps,
    optimize_oe_subjects_after_scheduling,
    schedule_electives_globally,
    find_next_valid_day_for_electives,
    get_valid_dates_in_range
)
from generation import (
    save_to_excel,
    save_verification_excel,
    generate_pdf_timetable,
    create_download_link  # ← Added for completeness (optional)
)
from utils import (
    format_subject_display,
    format_elective_display,
    get_preferred_slot,
    calculate_end_time,
    normalize_date_to_ddmmyyyy
)

# Set page configuration for college selector
st.set_page_config(
    page_title="Exam Timetable Generator - College Selector",
    page_icon="calendar",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize session state for college selection
if 'selected_college' not in st.session_state:
    st.session_state.selected_college = None

def show_college_selector():
    """Display the college selector landing page"""
    st.markdown(CSS_COLLEGE_SELECTOR, unsafe_allow_html=True)
    st.markdown("""
    <div class="main-header">
        <h1>Exam Timetable Generator</h1>
        <p>SVKM's NMIMS University</p>
        <p style="font-size: 1rem; margin-top: 1rem;">Select Your School/College</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### Choose Your School")
    st.markdown("Select the school for which you want to generate the exam timetable:")

    # Create columns for better layout (3 colleges per row)
    cols_per_row = 3
    num_colleges = len(COLLEGES)
    
    for i in range(0, num_colleges, cols_per_row):
        cols = st.columns(cols_per_row)
        for j in range(cols_per_row):
            idx = i + j
            if idx < num_colleges:
                college = COLLEGES[idx]
                with cols[j]:
                    if st.button(
                        f"{college['icon']}\n\n{college['name']}", 
                        key=f"college_{idx}",
                        use_container_width=True
                    ):
                        st.session_state.selected_college = college['name']
                        st.rerun()

    # Footer
    st.markdown("---")
    st.markdown("""
    <div class="footer">
        <p><strong>Unified Exam Timetable Generation System</strong></p>
        <p>SVKM's Narsee Monjee Institute of Management Studies (NMIMS)</p>
        <p style="font-size: 0.9em; margin-top: 1rem;">
            Intelligent Scheduling • Conflict Resolution • Multi-Campus Support
        </p>
    </div>
    """, unsafe_allow_html=True)

def main():
    # Check if college is selected
    if st.session_state.selected_college is None:
        show_college_selector()
        return
    
    # === GET SELECTED COLLEGE NAME ===
    selected_college_name = st.session_state.selected_college

    # Display selected college in sidebar
    with st.sidebar:
        st.markdown(f"### Selected School")
        st.info(selected_college_name)
        
        if st.button("Change School", use_container_width=True):
            st.session_state.selected_college = None
            # Clear all timetable data when changing school
            for key in list(st.session_state.keys()):
                if key != 'selected_college':
                    del st.session_state[key]
            st.rerun()
        
        st.markdown("---")

    # Set page configuration for main app
    st.set_page_config(
        page_title="Exam Timetable Generator",
        page_icon="calendar",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    st.markdown(CSS_MAIN_APP, unsafe_allow_html=True)

    st.markdown("""
    <div class="main-header">
        <h1>Exam Timetable Generator</h1>
        <p>MUKESH PATEL SCHOOL OF TECHNOLOGY MANAGEMENT & ENGINEERING</p>
    </div>
    """, unsafe_allow_html=True)

    # Initialize session state variables if not present
    init_session_state()

    with st.sidebar:
        configure_sidebar()

    # Main UI and processing
    process_upload_and_generate()

    # Display results if complete
    if st.session_state.get('processing_complete', False):
        display_results()

    # Footer
    display_footer()

def init_session_state():
    """Initialize all session state variables."""
    defaults = {
        'num_custom_holidays': 1,
        'custom_holidays': [None],
        'timetable_data': {},
        'processing_complete': False,
        'excel_data': None,
        'pdf_data': None,
        'verification_data': None,
        'total_exams': 0,
        'total_semesters': 0,
        'total_branches': 0,
        'overall_date_range': 0,
        'unique_exam_days': 0,
        'capacity_slider': 2000,
        'holidays_set': set(),
        'original_df': None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def configure_sidebar():
    """Configure the sidebar with date, holidays, and capacity settings."""
    st.markdown("### Configuration")
    st.markdown("#### Examination Period")

    col1, col2 = st.columns(2)
    with col1:
        base_date_input = st.date_input(
            "Start date for exams",
            value=datetime(2025, 4, 1),
            key="base_date_input"
        )
    with col2:
        end_date_input = st.date_input(
            "End date for exams",
            value=datetime(2025, 5, 30),
            key="end_date_input"
        )

    base_date = datetime.combine(base_date_input, datetime.min.time())
    end_date = datetime.combine(end_date_input, datetime.min.time())

    if end_date <= base_date:
        st.error("End date must be after start date!")
        end_date = base_date + timedelta(days=30)
        st.warning(f"Auto-corrected end date to: {end_date.strftime('%Y-%m-%d')}")

    st.session_state.base_date = base_date
    st.session_state.end_date = end_date

    st.markdown('<div style="margin-top: 2rem;"></div>', unsafe_allow_html=True)
    st.markdown("#### Capacity Configuration")

    if "capacity_slider" not in st.session_state:
        st.session_state.capacity_slider = 2000

    st.slider(
        "Maximum Students Per Session",
        min_value=1000,
        max_value=3000,
        value=st.session_state.capacity_slider,
        step=100,
        help="Set the maximum number of students allowed in a single session (morning or afternoon)",
        key="capacity_slider"
    )

    st.info(f"Current capacity: **{st.session_state.capacity_slider}** students per session")

    st.markdown('<div style="margin-top: 2rem;"></div>', unsafe_allow_html=True)

    with st.expander("Holiday Configuration", expanded=True):
        configure_holidays()

def configure_holidays():
    """Configure holidays in sidebar."""
    st.markdown("#### Select Predefined Holidays")
    
    holiday_dates = []

    col1, col2 = st.columns(2)
    with col1:
        if st.checkbox("April 14, 2025", value=True):
            holiday_dates.append(datetime(2025, 4, 14).date())
    with col2:
        if st.checkbox("May 1, 2025", value=True):
            holiday_dates.append(datetime(2025, 5, 1).date())

    if st.checkbox("August 15, 2025", value=True):
        holiday_dates.append(datetime(2025, 8, 15).date())

    st.markdown("#### Add Custom Holidays")
    if len(st.session_state.custom_holidays) < st.session_state.num_custom_holidays:
        st.session_state.custom_holidays.extend(
            [None] * (st.session_state.num_custom_holidays - len(st.session_state.custom_holidays))
        )

    for i in range(st.session_state.num_custom_holidays):
        st.session_state.custom_holidays[i] = st.date_input(
            f"Custom Holiday {i + 1}",
            value=st.session_state.custom_holidays[i],
            key=f"custom_holiday_{i}"
        )

    if st.button("Add Another Holiday"):
        st.session_state.num_custom_holidays += 1
        st.session_state.custom_holidays.append(None)
        st.rerun()

    custom_holidays = [h for h in st.session_state.custom_holidays if h is not None]
    for custom_holiday in custom_holidays:
        holiday_dates.append(custom_holiday)

    holidays_set = set(holiday_dates)
    st.session_state.holidays_set = holidays_set

    if holidays_set:
        st.markdown("#### Selected Holidays:")
        for holiday in sorted(holidays_set):
            st.write(f"• {holiday.strftime('%B %d, %Y')}")

def process_upload_and_generate():
    """Handle file upload and timetable generation."""
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("""
        <div class="upload-section">
            <h3>Upload Excel File</h3>
            <p>Upload your timetable data file (.xlsx format)</p>
        </div>
        """, unsafe_allow_html=True)

        uploaded_file = st.file_uploader(
            "Choose an Excel file",
            type=['xlsx', 'xls'],
            help="Upload the Excel file containing your timetable data"
        )

        if uploaded_file is not None:
            st.markdown('<div class="status-success">File uploaded successfully!</div>', unsafe_allow_html=True)

            file_details = {
                "Filename": uploaded_file.name,
                "File size": f"{uploaded_file.size / 1024:.2f} KB",
                "File type": uploaded_file.type
            }

            st.markdown("#### File Details:")
            for key, value in file_details.items():
                st.write(f"**{key}:** {value}")

            st.session_state.uploaded_file = uploaded_file

    with col2:
        st.markdown("""
        <div class="feature-card">
            <h4>Features</h4>
            <ul>
                <li>Excel file processing</li>
                <li>Common across semesters first</li>
                <li>Common within semester scheduling</li>
                <li>Gap-filling optimization</li>
                <li>Stream-wise uncommon scheduling</li>
                <li>OE elective optimization</li>
                <li>One exam per day per branch</li>
                <li>PDF generation</li>
                <li>Verification file export</li>
                <li>Three-phase priority scheduling</li>
                <li>Mobile-friendly interface</li>
                <li>Date range enforcement</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    if st.session_state.get('uploaded_file') is not None:
        if st.button("Generate Timetable", type="primary", use_container_width=True):
            with st.spinner("Processing your timetable... Please wait..."):
                try:
                    base_date = st.session_state.base_date
                    end_date = st.session_state.end_date
                    holidays_set = st.session_state.holidays_set
                    max_capacity = st.session_state.capacity_slider
                    uploaded_file = st.session_state.uploaded_file

                    date_range_days = (end_date - base_date).days + 1
                    valid_exam_days = len(get_valid_dates_in_range(base_date, end_date, holidays_set))
                    st.info(f"Examination Period: {base_date.strftime('%d-%m-%Y')} to {end_date.strftime('%d-%m-%Y')} ({date_range_days} total days, {valid_exam_days} valid exam days)")
                
                    df_non_elec, df_ele, original_df = read_timetable(uploaded_file)

                    if df_non_elec is not None and not df_non_elec.empty:
                        df_scheduled = schedule_all_subjects_comprehensively(df_non_elec, holidays_set, base_date, end_date, MAX_STUDENTS_PER_SESSION=max_capacity)

                        sem_dict_temp = {}
                        for s in sorted(df_scheduled["Semester"].unique()):
                            sem_data = df_scheduled[df_scheduled["Semester"] == s].copy()
                            sem_dict_temp[s] = sem_data    

                        is_valid, violations = validate_capacity_constraints(
                            sem_dict_temp, 
                            max_capacity=max_capacity
                        )

                        if is_valid:
                            st.success(f"All sessions meet the {max_capacity}-student capacity constraint!")
                        else:
                            st.error(f"{len(violations)} session(s) exceed capacity:")
                            for v in violations:
                                st.warning(
                                    f"  • {v['date']} at {v['time_slot']}: "
                                    f"{v['student_count']} students ({v['excess']} over {max_capacity} limit, "
                                    f"{v['subjects_count']} subjects)"
                                )

                        max_non_elec_date = None
                        non_elec_dates = pd.to_datetime(df_scheduled['Exam Date'], format="%d-%m-%Y", errors='coerce').dropna()
                        if not non_elec_dates.empty:
                            max_non_elec_date = max(non_elec_dates).date()
                        
                        all_scheduled_subjects = df_scheduled
                        if df_ele is not None and not df_ele.empty:
                            all_scheduled_subjects = handle_electives(df_scheduled, df_ele, end_date, holidays_set, max_non_elec_date)
                        
                        successfully_scheduled = all_scheduled_subjects[
                            (all_scheduled_subjects['Exam Date'] != "") & 
                            (all_scheduled_subjects['Exam Date'] != "Out of Range")
                        ].copy()
                        
                        out_of_range_subjects = all_scheduled_subjects[
                            all_scheduled_subjects['Exam Date'] == "Out of Range"
                        ]
                        
                        if not out_of_range_subjects.empty:
                            st.warning(f"{len(out_of_range_subjects)} subjects could not be scheduled within the specified date range")
                            
                            with st.expander("Subjects Not Scheduled (Out of Range)"):
                                for semester in sorted(out_of_range_subjects['Semester'].unique()):
                                    sem_subjects = out_of_range_subjects[out_of_range_subjects['Semester'] == semester]
                                    st.write(f"**Semester {semester}:** {len(sem_subjects)} subjects")
                                    for branch in sorted(sem_subjects['Branch'].unique()):
                                        branch_subjects = sem_subjects[sem_subjects['Branch'] == branch]
                                        st.write(f"  • {branch}: {len(branch_subjects)} subjects")
                        
                        if not successfully_scheduled.empty:
                            successfully_scheduled = successfully_scheduled.sort_values(["Semester", "Exam Date"], ascending=True)
                            
                            sem_dict = {}
                            for s in sorted(successfully_scheduled["Semester"].unique()):
                                sem_data = successfully_scheduled[successfully_scheduled["Semester"] == s].copy()
                                sem_dict[s] = sem_data
                            
                            sem_dict, gap_moves_made, gap_optimization_log = optimize_schedule_by_filling_gaps(
                                sem_dict, holidays_set, base_date, end_date
                            )

                            oe_moves_made = 0
                            oe_optimization_log = []
                            if df_ele is not None and not df_ele.empty:
                                sem_dict, oe_moves_made, oe_optimization_log = optimize_oe_subjects_after_scheduling(sem_dict, holidays_set)        

                            total_optimizations = oe_moves_made + gap_moves_made
                            if total_optimizations > 0:
                                st.success(f"Total Optimizations Made: {total_optimizations}")
                            if oe_moves_made > 0:
                                st.info(f"OE Optimizations: {oe_moves_made}")
                            if gap_moves_made > 0:
                                st.info(f"Gap Fill Optimizations: {gap_moves_made}")

                            st.session_state.timetable_data = sem_dict
                            st.session_state.original_df = original_df
                            st.session_state.processing_complete = True

                            compute_and_store_stats(sem_dict, valid_exam_days)

                            # === PASS COLLEGE NAME TO GENERATION ===
                            generate_files(sem_dict, original_df, selected_college_name)

                            st.markdown('<div class="status-success">Timetable generated successfully with THREE-PHASE SCHEDULING and NO DOUBLE BOOKINGS!</div>',
                                        unsafe_allow_html=True)
                            
                            display_scheduling_summary(valid_exam_days)
                            
                            st.success("**No Double Bookings**: Each subbranch has max one exam per day")
                            

                        else:
                            st.warning("No subjects could be scheduled within the specified date range.")

                    else:
                        st.markdown(
                            '<div class="status-error">Failed to read the Excel file. Please check the format.</div>',
                            unsafe_allow_html=True)

                except Exception as e:
                    st.markdown(f'<div class="status-error">An error occurred: {str(e)}</div>',
                                unsafe_allow_html=True)

def handle_electives(df_scheduled, df_ele, end_date, holidays_set, max_non_elec_date):
    if max_non_elec_date is None:
        non_elec_dates = pd.to_datetime(df_scheduled['Exam Date'], format="%d-%m-%Y", errors='coerce').dropna()
        if not non_elec_dates.empty:
            max_non_elec_date = max(non_elec_dates).date()
    
    elective_day1 = find_next_valid_day_for_electives(
        datetime.combine(max_non_elec_date, datetime.min.time()) + timedelta(days=1), 
        holidays_set
    )
    elective_day2 = find_next_valid_day_for_electives(elective_day1 + timedelta(days=1), holidays_set)
    
    if elective_day2 <= end_date:
        df_ele_scheduled = schedule_electives_globally(df_ele, max_non_elec_date, holidays_set)
        all_scheduled_subjects = pd.concat([df_scheduled, df_ele_scheduled], ignore_index=True)
    else:
        st.warning(f"Electives cannot be scheduled within end date ({end_date.strftime('%d-%m-%Y')})")
        all_scheduled_subjects = df_scheduled
    return all_scheduled_subjects

def compute_and_store_stats(sem_dict, valid_exam_days):
    final_all_data = pd.concat(sem_dict.values(), ignore_index=True)
    total_exams = len(final_all_data)
    total_semesters = len(sem_dict)
    total_branches = len(final_all_data['Branch'].unique())

    all_dates = pd.to_datetime(final_all_data['Exam Date'], format="%d-%m-%Y", errors='coerce').dropna()
    overall_date_range = (max(all_dates) - min(all_dates)).days + 1 if len(all_dates) > 0 else 0
    unique_exam_days = len(all_dates.dt.date.unique())

    st.session_state.total_exams = total_exams
    st.session_state.total_semesters = total_semesters
    st.session_state.total_branches = total_branches
    st.session_state.overall_date_range = overall_date_range
    st.session_state.unique_exam_days = unique_exam_days

# === FIXED generate_files() WITH COLLEGE NAME ===
def generate_files(sem_dict, original_df, college_name):
    """Generate Excel, PDF, and verification files."""
    # Generate Excel
    try:
        excel_buffer = save_to_excel(sem_dict, college_name)  # ← PASSED college_name
        if excel_buffer:
            st.session_state.excel_data = excel_buffer.getvalue()
            st.success("Excel file generated successfully")
        else:
            st.warning("Excel generation completed but no data returned")
            st.session_state.excel_data = None
    except Exception as e:
        st.error(f"Excel generation failed: {str(e)}")
        st.session_state.excel_data = None

    # Generate verification file
    try:
        verification_buffer = save_verification_excel(sem_dict, college_name)  # ← PASSED sem_dict + college_name
        if verification_buffer:
            st.session_state.verification_data = verification_buffer.getvalue()
            st.success("Verification file generated successfully")
        else:
            st.warning("Verification file generation completed but no data returned")
            st.session_state.verification_data = None
    except Exception as e:
        st.error(f"Verification file generation failed: {str(e)}")
        st.session_state.verification_data = None

    # Generate PDF
    try:
        if sem_dict:
            pdf_buffer = io.BytesIO()
            temp_pdf_path = "temp_timetable.pdf"
            generate_pdf_timetable(sem_dict, college_name)  # ← PASSED college_name
            
            if os.path.exists(temp_pdf_path):
                with open(temp_pdf_path, "rb") as f:
                    pdf_buffer.write(f.read())
                pdf_buffer.seek(0)
                st.session_state.pdf_data = pdf_buffer.getvalue()
                os.remove(temp_pdf_path)
                st.success("PDF generated successfully")
            else:
                st.warning("PDF generation completed but file not found")
                st.session_state.pdf_data = None
        else:
            st.warning("No data available for PDF generation")
            st.session_state.pdf_data = None
    except Exception as e:
        st.error(f"PDF generation failed: {str(e)}")
        st.session_state.pdf_data = None

# === REST OF YOUR CODE UNCHANGED (display_scheduling_summary, display_results, etc.) ===
# [All remaining functions below are 100% unchanged]

def display_scheduling_summary(valid_exam_days):
    st.info("**Three-Phase Scheduling Applied:**\n1. **Phase 1:** Common across semesters scheduled FIRST from base date\n2. **Phase 2:** Common within semester subjects (COMP/ELEC appearing in multiple branches)\n3. **Phase 3:** Truly uncommon subjects with gap-filling optimization within date range\n4. **Phase 4:** Electives scheduled LAST (if space available)\n5. **Guarantee:** ONE exam per day per subbranch-semester")
    
    efficiency = (st.session_state.unique_exam_days / st.session_state.overall_date_range) * 100 if st.session_state.overall_date_range > 0 else 0
    st.success(f"**Schedule Efficiency: {efficiency:.1f}%** (Higher is better - more days utilized)")
    
    date_range_utilization = (st.session_state.unique_exam_days / valid_exam_days) * 100 if valid_exam_days > 0 else 0
    st.info(f"**Date Range Utilization: {date_range_utilization:.1f}%** ({st.session_state.unique_exam_days}/{valid_exam_days} valid days used)")
    
    final_all_data = pd.concat(st.session_state.timetable_data.values(), ignore_index=True)
    common_across_count = len(final_all_data[final_all_data['CommonAcrossSems'] == True])
    
    common_within_sem = final_all_data[
        (final_all_data['CommonAcrossSems'] == False) & 
        (final_all_data['Category'].isin(['COMP', 'ELEC']))
    ]
    common_within_sem_groups = common_within_sem.groupby(['Semester', 'ModuleCode'])['Branch'].nunique()
    common_within_count = len(common_within_sem[
        common_within_sem.set_index(['Semester', 'ModuleCode']).index.map(
            lambda x: common_within_sem_groups.get(x, 1) > 1
        )
    ])
    
    elective_count = len(final_all_data[final_all_data['OE'].notna() & (final_all_data['OE'].str.strip() != "")])
    uncommon_count = st.session_state.total_exams - common_across_count - common_within_count - elective_count
    
    st.success(f"**Scheduling Breakdown:**\n• Common Across Semesters: {common_across_count}\n• Common Within Semester: {common_within_count}\n• Truly Uncommon: {uncommon_count}\n• Electives: {elective_count}")

def display_results():
    st.markdown("---")
    st.markdown("### Download Options")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        if st.session_state.excel_data:
            st.download_button(
                label="Download Excel File",
                data=st.session_state.excel_data,
                file_name=f"complete_timetable_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="download_excel"
            )
        else:
            st.button("Excel Not Available", disabled=True, use_container_width=True)

    with col2:
        if st.session_state.pdf_data:
            st.download_button(
                label="Download PDF File",
                data=st.session_state.pdf_data,
                file_name=f"complete_timetable_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="download_pdf"
            )
        else:
            st.button("PDF Not Available", disabled=True, use_container_width=True)

    with col3:
        if st.session_state.verification_data:
            st.download_button(
                label="Download Verification File",
                data=st.session_state.verification_data,
                file_name=f"verification_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="download_verification"
            )
        else:
            st.button("Verification Not Available", disabled=True, use_container_width=True)

    with col4:
        st.link_button("Re-upload Verification File", "https://verification-file-change-to-pdf-converter.streamlit.app/", use_container_width=True)
       
    with col5:
        if st.button("Generate New Timetable", use_container_width=True):
            st.session_state.processing_complete = False
            st.session_state.timetable_data = {}
            st.session_state.original_df = None
            st.session_state.excel_data = None
            st.session_state.pdf_data = None
            st.session_state.verification_data = None
            st.session_state.total_exams = 0
            st.session_state.total_semesters = 0
            st.session_state.total_branches = 0
            st.session_state.overall_date_range = 0
            st.session_state.unique_exam_days = 0
            st.session_state.uploaded_file = None
            st.rerun()

    display_statistics()
    display_timetable()

def display_statistics():
    st.markdown("""
    <div class="stats-section">
        <h2>Complete Timetable Statistics</h2>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.timetable_data:
        final_all_data = pd.concat(st.session_state.timetable_data.values(), ignore_index=True)
    
        non_elective_data = final_all_data[~(final_all_data['OE'].notna() & (final_all_data['OE'].str.strip() != ""))]
        oe_data = final_all_data[final_all_data['OE'].notna() & (final_all_data['OE'].str.strip() != "")]

        non_elec_display = "No data"
        if not non_elective_data.empty:
            non_elec_dates = pd.to_datetime(non_elective_data['Exam Date'], format="%d-%m-%Y", errors='coerce').dropna()
            if not non_elec_dates.empty:
                non_elec_range = (max(non_elec_dates) - min(non_elec_dates)).days + 1
                non_elec_start = min(non_elec_dates).strftime("%d %B")
                non_elec_end = max(non_elec_dates).strftime("%d %B")
                non_elec_display = f"{non_elec_start} to {non_elec_end}" if non_elec_start != non_elec_end else non_elec_start

        oe_display = "No OE subjects"
        if not oe_data.empty:
            oe_dates = pd.to_datetime(oe_data['Exam Date'], format="%d-%m-%Y", errors='coerce').dropna()
            if not oe_dates.empty:
                unique_oe_dates = sorted(oe_dates.dt.strftime("%d %B").unique())
                oe_display = ", ".join(unique_oe_dates[:2]) if len(unique_oe_dates) <= 2 else f"{unique_oe_dates[0]} to {unique_oe_dates[-1]}"

        gap_display = "N/A"
        if not non_elective_data.empty and not oe_data.empty:
            non_elec_dates = pd.to_datetime(non_elective_data['Exam Date'], format="%d-%m-%Y", errors='coerce').dropna()
            oe_dates = pd.to_datetime(oe_data['Exam Date'], format="%d-%m-%Y", errors='coerce').dropna()
            if not non_elec_dates.empty and not oe_dates.empty:
                max_non_elec = max(non_elec_dates)
                min_oe = min(oe_dates)
                gap_days = (min_oe - max_non_elec).days - 1
                gap_display = f"{max(0, gap_days)} days"

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-card"><h3>{st.session_state.total_exams}</h3><p>Total Exams</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card"><h3>{st.session_state.total_semesters}</h3><p>Semesters</p></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-card"><h3>{st.session_state.total_branches}</h3><p>Branches</p></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="metric-card"><h3>{st.session_state.overall_date_range}</h3><p>Overall Span</p></div>', unsafe_allow_html=True)

    st.markdown("### Examination Schedule Breakdown")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="metric-card" style="text-align: left; padding: 1rem;">
            <h4 style="margin: 0; color: white;">Non-Elective Exams</h4>
            <p style="margin: 0.5rem 0 0 0; font-size: 1rem; opacity: 0.9;">{non_elec_display}</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card" style="text-align: left; padding: 1rem;">
            <h4 style="margin: 0; color: white;">Open Elective (OE) Exams</h4>
            <p style="margin: 0.5rem 0 0 0; font-size: 1rem; opacity: 0.9;">{oe_display}</p>
        </div>
        """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'<div class="metric-card"><h3>{st.session_state.unique_exam_days}</h3><p>Unique Exam Days</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card"><h3>{gap_display}</h3><p>Non-Elec to OE Gap</p></div>', unsafe_allow_html=True)
    with col3:
        efficiency = (st.session_state.unique_exam_days / st.session_state.overall_date_range) * 100 if st.session_state.overall_date_range > 0 else 0
        st.markdown(f'<div class="metric-card"><h3>{efficiency:.1f}%</h3><p>Schedule Efficiency</p></div>', unsafe_allow_html=True)

    total_possible_slots = st.session_state.overall_date_range * 2
    actual_exams = st.session_state.total_exams
    slot_utilization = min(100, (actual_exams / total_possible_slots * 100)) if total_possible_slots > 0 else 0
    
    if slot_utilization > 70:
        st.success(f"**Slot Utilization:** {slot_utilization:.1f}% (Excellent optimization)")
    elif slot_utilization > 50:
        st.info(f"**Slot Utilization:** {slot_utilization:.1f}% (Good optimization)")
    else:
        st.warning(f"**Slot Utilization:** {slot_utilization:.1f}% (Room for improvement)")

def display_timetable():
    st.markdown("""
    <div class="results-section">
        <h2>Complete Timetable Results</h2>
    </div>
    """, unsafe_allow_html=True)

    def format_subject_display(row):
        subject = row['Subject']
        time_slot = row['Time Slot']
        duration = row.get('Exam Duration', 3)
        is_common = row.get('CommonAcrossSems', False)
        semester = row['Semester']
        cm_group = str(row.get('CMGroup', '')).strip()
        cm_group_prefix = f"[{cm_group}] " if cm_group and cm_group != "" and cm_group != "nan" else ""
        preferred_slot = get_preferred_slot(semester)
        time_range = ""
        if duration != 3 and time_slot and time_slot.strip():
            start_time = time_slot.split(' - ')[0].strip()
            end_time = calculate_end_time(start_time, duration)
            time_range = f" ({start_time} - {end_time})"
        elif is_common and time_slot != preferred_slot and time_slot and time_slot.strip():
            time_range = f" ({time_slot})"
        return cm_group_prefix + subject + time_range

    def format_elective_display(row):
        subject = row['Subject']
        oe_type = row.get('OE', '')
        cm_group = str(row.get('CMGroup', '')).strip()
        cm_group_prefix = f"[{cm_group}] " if cm_group and cm_group != "" and cm_group != "nan" else ""
        base_display = f"{cm_group_prefix}{subject} [{oe_type}]" if oe_type else cm_group_prefix + subject
        duration = row.get('Exam Duration', 3)
        time_slot = row['Time Slot']
        if duration != 3 and time_slot and time_slot.strip():
            start_time = time_slot.split(' - ')[0].strip()
            end_time = calculate_end_time(start_time, duration)
            time_range = f" ({start_time} - {end_time})"
        else:
            time_range = ""
        return base_display + time_range

    for sem, df_sem in st.session_state.timetable_data.items():
        st.markdown(f"### Semester {sem}")

        for main_branch in df_sem["MainBranch"].unique():
            main_branch_full = BRANCH_FULL_FORM.get(main_branch, main_branch)
            df_mb = df_sem[df_sem["MainBranch"] == main_branch].copy()

            if not df_mb.empty:
                df_non_elec = df_mb[df_mb['OE'].isna() | (df_mb['OE'].str.strip() == "")].copy()
                df_elec = df_mb[df_mb['OE'].notna() & (df_mb['OE'].str.strip() != "")].copy()

                if not df_non_elec.empty:
                    st.markdown(f"#### {main_branch_full} - Core Subjects")
                    try:
                        df_non_elec["SubjectDisplay"] = df_non_elec.apply(format_subject_display, axis=1)
                        df_non_elec["Exam Date"] = pd.to_datetime(df_non_elec["Exam Date"], format="%d-%m-%Y", errors='coerce')
                        df_non_elec = df_non_elec.sort_values(by="Exam Date", ascending=True)
                       
                        display_data = []
                        for date, group in df_non_elec.groupby('Exam Date'):
                            date_str = date.strftime("%d-%m-%Y") if pd.notna(date) else "Unknown Date"
                            row_data = {'Exam Date': date_str}
                            for subbranch in df_non_elec['SubBranch'].unique():
                                subbranch_subjects = group[group['SubBranch'] == subbranch]['SubjectDisplay'].tolist()
                                row_data[subbranch] = ", ".join(subbranch_subjects) if subbranch_subjects else "---"
                            display_data.append(row_data)
                       
                        if display_data:
                            display_df = pd.DataFrame(display_data).set_index('Exam Date')
                            st.dataframe(display_df, use_container_width=True)
                        else:
                            st.write("No core subjects to display")
                       
                    except Exception as e:
                        st.error(f"Error displaying core subjects: {str(e)}")
                        st.write("Showing raw data:")
                        display_cols = ['Exam Date', 'SubBranch', 'Subject', 'Time Slot']
                        available_cols = [col for col in display_cols if col in df_non_elec.columns]
                        st.dataframe(df_non_elec[available_cols], use_container_width=True)

                if not df_elec.empty:
                    st.markdown(f"#### {main_branch_full} - Open Electives")
                    try:
                        df_elec["SubjectDisplay"] = df_elec.apply(format_elective_display, axis=1)
                        df_elec["Exam Date"] = pd.to_datetime(df_elec["Exam Date"], format="%d-%m-%Y", errors='coerce')
                        df_elec = df_elec.sort_values(by="Exam Date", ascending=True)
                       
                        elec_display_data = []
                        for (oe_type, date), group in df_elec.groupby(['OE', 'Exam Date']):
                            date_str = date.strftime("%d-%m-%Y") if pd.notna(date) else "Unknown Date"
                            subjects = ", ".join(group['SubjectDisplay'].tolist())
                            elec_display_data.append({'Exam Date': date_str, 'OE Type': oe_type, 'Subjects': subjects})
                       
                        if elec_display_data:
                            elec_display_df = pd.DataFrame(elec_display_data)
                            st.dataframe(elec_display_df, use_container_width=True)
                        else:
                            st.write("No elective subjects to display")
                       
                    except Exception as e:
                        st.error(f"Error displaying elective subjects: {str(e)}")
                        st.write("Showing raw data:")
                        display_cols = ['Exam Date', 'OE', 'Subject', 'Time Slot']
                        available_cols = [col for col in display_cols if col in df_elec.columns]
                        st.dataframe(df_elec[available_cols], use_container_width=True)

def display_footer():
    st.markdown("---")
    st.markdown("""
    <div class="footer">
        <p><strong>Three-Phase Timetable Generator with Date Range Control & Gap-Filling</strong></p>
        <p>Developed for MUKESH PATEL SCHOOL OF TECHNOLOGY MANAGEMENT & ENGINEERING</p>
        <p style="font-size: 0.9em;">Common across semesters first • Common within semester • Gap-filling optimization • One exam per day per branch • OE optimization • Date range enforcement • Maximum efficiency • Verification export</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
