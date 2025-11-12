import streamlit as st
from datetime import datetime, timedelta
import pandas as pd

# Import custom modules
from config import (
    COLLEGES, 
    BRANCH_FULL_FORM, 
    LOGO_PATH,
    setup_page_config,
    apply_custom_css
)
from ui_components import (
    show_college_selector,
    display_header,
    display_sidebar_config,
    display_statistics,
    display_timetable_results
)
from data_processing import (
    read_timetable,
    get_valid_dates_in_range
)
from scheduling import (
    schedule_all_subjects_comprehensively,
    schedule_electives_globally,
    optimize_schedule_by_filling_gaps,
    optimize_oe_subjects_after_scheduling,
    validate_capacity_constraints
)
from file_generation import (
    save_to_excel,
    save_verification_excel,
    generate_pdf_timetable
)
from session_manager import initialize_session_state


def main():
    """Main application entry point"""
    # Setup page configuration
    setup_page_config()
    
    # Apply custom CSS
    apply_custom_css()
    
    # Initialize session state
    initialize_session_state()
    
    # Check if college is selected
    if st.session_state.selected_college is None:
        show_college_selector()
        return
    
    # Display selected college in sidebar
    with st.sidebar:
        st.markdown(f"### 🏫 Selected School")
        st.info(st.session_state.selected_college)
        
        if st.button("🔙 Change School", use_container_width=True):
            st.session_state.selected_college = None
            # Clear all timetable data when changing school
            for key in list(st.session_state.keys()):
                if key != 'selected_college':
                    del st.session_state[key]
            st.rerun()
        
        st.markdown("---")
    
    # Display header
    display_header()
    
    # Get configuration from sidebar
    config = display_sidebar_config()
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        <div class="upload-section">
            <h3>📁 Upload Excel File</h3>
            <p>Upload your timetable data file (.xlsx format)</p>
        </div>
        """, unsafe_allow_html=True)
        
        uploaded_file = st.file_uploader(
            "Choose an Excel file",
            type=['xlsx', 'xls'],
            help="Upload the Excel file containing your timetable data"
        )
        
        if uploaded_file is not None:
            st.markdown('<div class="status-success">✅ File uploaded successfully!</div>', 
                       unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="feature-card">
            <h4>🚀 Features</h4>
            <ul>
                <li>📊 Excel file processing</li>
                <li>🎯 Common across semesters first</li>
                <li>🔗 Common within semester scheduling</li>
                <li>🔍 Gap-filling optimization</li>
                <li>🔄 Stream-wise uncommon scheduling</li>
                <li>🎓 OE elective optimization</li>
                <li>⚡ One exam per day per branch</li>
                <li>📋 PDF generation</li>
                <li>✅ Verification file export</li>
                <li>🎯 Three-phase priority scheduling</li>
                <li>💥 Capacity constraint enforcement</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # Process timetable generation
    if uploaded_file is not None:
        if st.button("🔄 Generate Timetable", type="primary", use_container_width=True):
            process_timetable_generation(uploaded_file, config)
    
    # Display results if processing is complete
    if st.session_state.processing_complete:
        display_results(config)
    
    # Footer
    display_footer()


def process_timetable_generation(uploaded_file, config):
    """Process timetable generation with all scheduling phases"""
    with st.spinner("Processing your timetable... Please wait..."):
        try:
            # Extract configuration
            base_date = config['base_date']
            end_date = config['end_date']
            holidays_set = config['holidays_set']
            max_capacity = config['max_capacity']
            
            # Validate date range
            if end_date <= base_date:
                st.error("❌ End date must be after start date!")
                return
            
            # Display date range info
            valid_exam_days = len(get_valid_dates_in_range(base_date, end_date, holidays_set))
            st.info(f"📅 Examination Period: {base_date.strftime('%d-%m-%Y')} to {end_date.strftime('%d-%m-%Y')} ({valid_exam_days} valid exam days)")
            
            # Read timetable data
            df_non_elec, df_ele, original_df = read_timetable(uploaded_file)
            
            if df_non_elec is None:
                st.error("❌ Failed to read the Excel file. Please check the format.")
                return
            
            # Schedule all subjects
            st.info("🚀 SUPER SCHEDULING: All subjects with frequency-based priority")
            df_scheduled = schedule_all_subjects_comprehensively(
                df_non_elec, holidays_set, base_date, end_date, max_capacity
            )
            
            # Validate capacity constraints
            sem_dict_temp = {}
            for s in sorted(df_scheduled["Semester"].unique()):
                sem_dict_temp[s] = df_scheduled[df_scheduled["Semester"] == s].copy()
            
            is_valid, violations = validate_capacity_constraints(sem_dict_temp, max_capacity)
            
            if is_valid:
                st.success(f"✅ All sessions meet the {max_capacity}-student capacity constraint!")
            else:
                st.error(f"⚠️ {len(violations)} session(s) exceed capacity:")
                for v in violations:
                    st.warning(f"  • {v['date']} at {v['time_slot']}: {v['student_count']} students")
            
            # Handle electives
            if df_ele is not None and not df_ele.empty:
                non_elec_dates = pd.to_datetime(df_scheduled['Exam Date'], format="%d-%m-%Y", errors='coerce').dropna()
                if not non_elec_dates.empty:
                    max_non_elec_date = max(non_elec_dates).date()
                    df_ele_scheduled = schedule_electives_globally(df_ele, max_non_elec_date, holidays_set)
                    all_scheduled_subjects = pd.concat([df_scheduled, df_ele_scheduled], ignore_index=True)
                else:
                    all_scheduled_subjects = df_scheduled
            else:
                all_scheduled_subjects = df_scheduled
            
            # Create semester dictionary
            successfully_scheduled = all_scheduled_subjects[
                (all_scheduled_subjects['Exam Date'] != "") & 
                (all_scheduled_subjects['Exam Date'] != "Out of Range")
            ].copy()
            
            if successfully_scheduled.empty:
                st.warning("No subjects could be scheduled within the specified date range.")
                return
            
            successfully_scheduled = successfully_scheduled.sort_values(["Semester", "Exam Date"], ascending=True)
            
            sem_dict = {}
            for s in sorted(successfully_scheduled["Semester"].unique()):
                sem_dict[s] = successfully_scheduled[successfully_scheduled["Semester"] == s].copy()
            
            # Optimize schedule
            sem_dict, gap_moves, _ = optimize_schedule_by_filling_gaps(
                sem_dict, holidays_set, base_date, end_date
            )
            
            if df_ele is not None and not df_ele.empty:
                sem_dict, oe_moves, _ = optimize_oe_subjects_after_scheduling(sem_dict, holidays_set)
            else:
                oe_moves = 0
            
            # Store results in session state
            store_results(sem_dict, original_df, gap_moves + oe_moves)
            
            st.success("🎉 Timetable generated successfully!")
            
        except Exception as e:
            st.error(f"❌ An error occurred: {str(e)}")


def store_results(sem_dict, original_df, total_optimizations):
    """Store generated results in session state"""
    st.session_state.timetable_data = sem_dict
    st.session_state.original_df = original_df
    st.session_state.processing_complete = True
    
    # Calculate statistics
    final_all_data = pd.concat(sem_dict.values(), ignore_index=True)
    st.session_state.total_exams = len(final_all_data)
    st.session_state.total_semesters = len(sem_dict)
    st.session_state.total_branches = len(set(final_all_data['Branch'].unique()))
    
    all_dates = pd.to_datetime(final_all_data['Exam Date'], format="%d-%m-%Y", errors='coerce').dropna()
    st.session_state.overall_date_range = (max(all_dates) - min(all_dates)).days + 1 if all_dates.size > 0 else 0
    st.session_state.unique_exam_days = len(all_dates.dt.date.unique())
    
    # Generate files
    try:
        excel_data = save_to_excel(sem_dict)
        st.session_state.excel_data = excel_data.getvalue() if excel_data else None
    except Exception as e:
        st.error(f"Excel generation failed: {str(e)}")
        st.session_state.excel_data = None
    
    try:
        verification_data = save_verification_excel(original_df, sem_dict)
        st.session_state.verification_data = verification_data.getvalue() if verification_data else None
    except Exception as e:
        st.error(f"Verification file generation failed: {str(e)}")
        st.session_state.verification_data = None
    
    try:
        import io
        import os
        pdf_output = io.BytesIO()
        temp_pdf_path = "temp_timetable.pdf"
        generate_pdf_timetable(sem_dict, temp_pdf_path)
        
        if os.path.exists(temp_pdf_path):
            with open(temp_pdf_path, "rb") as f:
                pdf_output.write(f.read())
            pdf_output.seek(0)
            st.session_state.pdf_data = pdf_output.getvalue()
            os.remove(temp_pdf_path)
        else:
            st.session_state.pdf_data = None
    except Exception as e:
        st.error(f"PDF generation failed: {str(e)}")
        st.session_state.pdf_data = None


def display_results(config):
    """Display timetable results and download options"""
    st.markdown("---")
    st.markdown("### 📥 Download Options")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        if st.session_state.excel_data:
            st.download_button(
                label="📊 Download Excel File",
                data=st.session_state.excel_data,
                file_name=f"complete_timetable_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        else:
            st.button("📊 Excel Not Available", disabled=True, use_container_width=True)
    
    with col2:
        if st.session_state.pdf_data:
            st.download_button(
                label="📄 Download PDF File",
                data=st.session_state.pdf_data,
                file_name=f"complete_timetable_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        else:
            st.button("📄 PDF Not Available", disabled=True, use_container_width=True)
    
    with col3:
        if st.session_state.verification_data:
            st.download_button(
                label="📋 Download Verification File",
                data=st.session_state.verification_data,
                file_name=f"verification_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        else:
            st.button("📋 Verification Not Available", disabled=True, use_container_width=True)
    
    with col4:
        st.link_button("♻️Re-upload Verification File", 
                      "https://verification-file-change-to-pdf-converter.streamlit.app/", 
                      use_container_width=True)
    
    with col5:
        if st.button("🔄 Generate New Timetable", use_container_width=True):
            for key in list(st.session_state.keys()):
                if key not in ['selected_college', 'capacity_slider']:
                    del st.session_state[key]
            st.session_state.processing_complete = False
            st.rerun()
    
    # Display statistics
    display_statistics()
    
    # Display timetable results
    display_timetable_results()


def display_footer():
    """Display application footer"""
    st.markdown("---")
    st.markdown("""
    <div class="footer">
        <p>🎓 <strong>Three-Phase Timetable Generator with Date Range Control & Gap-Filling</strong></p>
        <p>Developed for MUKESH PATEL SCHOOL OF TECHNOLOGY MANAGEMENT & ENGINEERING</p>
        <p style="font-size: 0.9em;">Common across semesters first • Common within semester • Gap-filling optimization • One exam per day per branch • OE optimization • Date range enforcement • Maximum efficiency • Verification export</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
