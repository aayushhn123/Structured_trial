import streamlit as st


def initialize_session_state():
    """Initialize all session state variables"""
    
    # College selection
    if 'selected_college' not in st.session_state:
        st.session_state.selected_college = None
    
    # Holiday configuration
    if 'num_custom_holidays' not in st.session_state:
        st.session_state.num_custom_holidays = 1
    if 'custom_holidays' not in st.session_state:
        st.session_state.custom_holidays = [None]
    
    # Timetable data
    if 'timetable_data' not in st.session_state:
        st.session_state.timetable_data = {}
    if 'processing_complete' not in st.session_state:
        st.session_state.processing_complete = False
    if 'original_df' not in st.session_state:
        st.session_state.original_df = None
    
    # Generated files
    if 'excel_data' not in st.session_state:
        st.session_state.excel_data = None
    if 'pdf_data' not in st.session_state:
        st.session_state.pdf_data = None
    if 'verification_data' not in st.session_state:
        st.session_state.verification_data = None
    
    # Statistics
    if 'total_exams' not in st.session_state:
        st.session_state.total_exams = 0
    if 'total_semesters' not in st.session_state:
        st.session_state.total_semesters = 0
    if 'total_branches' not in st.session_state:
        st.session_state.total_branches = 0
    if 'overall_date_range' not in st.session_state:
        st.session_state.overall_date_range = 0
    if 'unique_exam_days' not in st.session_state:
        st.session_state.unique_exam_days = 0
    
    # Capacity configuration
    if 'capacity_slider' not in st.session_state:
        st.session_state.capacity_slider = 2000
    
    # Holidays set
    if 'holidays_set' not in st.session_state:
        st.session_state.holidays_set = set()
