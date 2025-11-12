from datetime import datetime, timedelta
import pandas as pd
from fpdf import FPDF
from collections import defaultdict

# Cache for text wrapping results
wrap_text_cache = {}

def get_valid_dates_in_range(start_date, end_date, holidays_set):
    """
    Get all valid examination dates within the specified range.
    Excludes weekends (Sundays) and holidays.
    
    Args:
        start_date (datetime): Start date for examinations
        end_date (datetime): End date for examinations
        holidays_set (set): Set of holiday dates
    
    Returns:
        list: List of valid date strings in DD-MM-YYYY format
    """
    valid_dates = []
    current_date = start_date
    
    while current_date <= end_date:
        # Skip Sundays (weekday 6) and holidays
        if current_date.weekday() != 6 and current_date.date() not in holidays_set:
            valid_dates.append(current_date.strftime("%d-%m-%Y"))
        current_date += timedelta(days=1)
    
    return valid_dates

def find_next_valid_day_in_range(start_date, end_date, holidays_set):
    """
    Find the next valid examination day within the specified range.
    
    Args:
        start_date (datetime): Start date to search from
        end_date (datetime): End date limit
        holidays_set (set): Set of holiday dates
    
    Returns:
        datetime or None: Next valid date or None if no valid date found in range
    """
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() != 6 and current_date.date() not in holidays_set:
            return current_date
        current_date += timedelta(days=1)
    return None

def get_preferred_slot(semester, program_type="B TECH"):
    """Get preferred time slot based on semester and program type"""
    if semester % 2 != 0:  # Odd semester
        odd_sem_position = (semester + 1) // 2
        return "10:00 AM - 1:00 PM" if odd_sem_position % 2 == 1 else "2:00 PM - 5:00 PM"
    else:  # Even semester
        even_sem_position = semester // 2
        return "10:00 AM - 1:00 PM" if even_sem_position % 2 == 1 else "2:00 PM - 5:00 PM"

def get_preferred_slot_with_capacity(semester, date_str, session_capacity, student_count, max_capacity=2000):
    """Get preferred slot considering capacity constraints"""
    base_slot = get_preferred_slot(semester)
    
    if date_str not in session_capacity:
        return base_slot
    
    # Check if preferred slot has capacity
    session_type = 'morning' if '10:00 AM' in base_slot else 'afternoon'
    current_capacity = session_capacity[date_str].get(session_type, 0)
    
    if current_capacity + student_count <= max_capacity:
        return base_slot
    
    # Try alternate slot
    alternate_slot = "2:00 PM - 5:00 PM" if base_slot == "10:00 AM - 1:00 PM" else "10:00 AM - 1:00 PM"
    alternate_type = 'afternoon' if session_type == 'morning' else 'morning'
    alternate_capacity = session_capacity[date_str].get(alternate_type, 0)
    
    if alternate_capacity + student_count <= max_capacity:
        return alternate_slot
    
    # If neither fits, return None to indicate no slot available
    return None

def find_next_valid_day_for_electives(start_date, holidays_set):
    """
    Find next valid day for electives (skip Sundays/holidays).
    """
    current_date = start_date
    while True:
        if current_date.weekday() != 6 and current_date.date() not in holidays_set:
            return current_date
        current_date += timedelta(days=1)
    return None

def calculate_end_time(start_time, duration):
    """
    Calculate end time based on start time and duration (in hours).
    Assumes 12-hour format; simple addition for demo.
    """
    # Parse start time (e.g., "10:00 AM")
    time_str, period = start_time.split()
    hour, minute = map(int, time_str.split(':'))
    if period == 'PM' and hour != 12:
        hour += 12
    if period == 'AM' and hour == 12:
        hour = 0
    
    # Add duration
    total_minutes = hour * 60 + minute + (duration * 60)
    end_hour = (total_minutes // 60) % 24
    end_minute = total_minutes % 60
    
    # Format back
    end_period = 'AM' if end_hour < 12 else 'PM'
    if end_hour == 0:
        end_hour = 12
    elif end_hour > 12:
        end_hour -= 12
    return f"{end_hour:02d}:{end_minute:02d} {end_period}"

def normalize_date_to_ddmmyyyy(date_val):
    """Convert any date format to DD-MM-YYYY string format"""
    if pd.isna(date_val) or date_val == "":
        return ""
    
    if isinstance(date_val, pd.Timestamp):
        return date_val.strftime("%d-%m-%Y")
    elif isinstance(date_val, str):
        try:
            parsed = pd.to_datetime(date_val, format="%d-%m-%Y", errors='raise')
            return parsed.strftime("%d-%m-%Y")
        except:
            try:
                parsed = pd.to_datetime(date_val, dayfirst=True, errors='raise')
                return parsed.strftime("%d-%m-%Y")
            except:
                return str(date_val)
    else:
        try:
            parsed = pd.to_datetime(date_val, errors='coerce')
            if pd.notna(parsed):
                return parsed.strftime("%d-%m-%Y")
            else:
                return str(date_val)
        except:
            return str(date_val)

def format_subject_display(row):
    """Format subject display for non-electives in Streamlit interface"""
    subject = row['Subject']
    time_slot = row['Time Slot']
    duration = row.get('Exam Duration', 3)
    is_common = row.get('CommonAcrossSems', False)
    semester = row['Semester']

    # Add CM Group prefix
    cm_group = str(row.get('CMGroup', '')).strip()
    cm_group_prefix = f"[{cm_group}] " if cm_group and cm_group != "" else ""

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
    """Format subject display for electives in Streamlit interface"""
    subject = row['Subject']
    oe_type = row.get('OE', '')

    # Add CM Group prefix
    cm_group = str(row.get('CMGroup', '')).strip()
    cm_group_prefix = f"[{cm_group}] " if cm_group and cm_group != "" else ""

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

def wrap_text(pdf, text, col_width):
    """Wrap text for PDF generation."""
    cache_key = (text, col_width)
    if cache_key in wrap_text_cache:
        return wrap_text_cache[cache_key]
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        test_line = word if not current_line else current_line + " " + word
        if pdf.get_string_width(test_line) <= col_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    wrap_text_cache[cache_key] = lines
    return lines

def print_row_custom(pdf, row_data, col_widths, line_height=5, header=False):
    """Print custom row in PDF."""
    cell_padding = 2
    header_bg_color = (149, 33, 28)
    header_text_color = (255, 255, 255)
    alt_row_color = (240, 240, 240)

    row_number = getattr(pdf, '_row_counter', 0)
    if header:
        pdf.set_font("Arial", 'B', 10)
        pdf.set_text_color(*header_text_color)
        pdf.set_fill_color(*header_bg_color)
    else:
        pdf.set_font("Arial", size=10)
        pdf.set_text_color(0, 0, 0)
        pdf.set_fill_color(*alt_row_color if row_number % 2 == 1 else (255, 255, 255))

    wrapped_cells = []
    max_lines = 0
    for i, cell_text in enumerate(row_data):
        wrapped_lines = wrap_text(pdf, str(cell_text), col_widths[i])
        wrapped_cells.append(wrapped_lines)
        max_lines = max(max_lines, len(wrapped_lines))

    # Print multi-line cells
    for line_idx in range(max_lines):
        x_start = pdf.l_margin
        for i in range(len(row_data)):
            if line_idx < len(wrapped_cells[i]):
                pdf.cell(col_widths[i], line_height, wrapped_cells[i][line_idx], border=1, align='L')
            else:
                pdf.cell(col_widths[i], line_height, '', border=1, align='L')
            x_start += col_widths[i]
        pdf.ln(line_height)

    pdf._row_counter = row_number + 1
