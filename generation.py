import io
import os
import pandas as pd
from fpdf import FPDF
from utils import wrap_text, print_row_custom

def save_to_excel(sem_dict):
    """Save timetable to Excel bytes."""
    if not sem_dict:
        return None
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sem, df_sem in sem_dict.items():
            df_sem.to_excel(writer, sheet_name=f'Semester_{sem}', index=False)
    
    output.seek(0)
    return output

def save_verification_excel(original_df, sem_dict):
    """Save verification Excel with original vs scheduled comparison."""
    if original_df is None or not sem_dict:
        return None
    
    # Simple verification: Concat scheduled and add status column
    all_scheduled = pd.concat(sem_dict.values(), ignore_index=True)
    verification_df = original_df.merge(all_scheduled[['Subject', 'Exam Date', 'Time Slot']], on='Subject', how='left', suffixes=('', '_scheduled'))
    verification_df['Status'] = verification_df['Exam Date_scheduled'].apply(lambda x: 'Scheduled' if pd.notna(x) and x != '' else 'Pending')
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        verification_df.to_excel(writer, sheet_name='Verification', index=False)
    
    output.seek(0)
    return output

def generate_pdf_timetable(sem_dict, output_path):
    """Generate PDF timetable using FPDF."""
    if not sem_dict:
        return
    
    pdf = FPDF(orientation='L', unit='mm', format='A4')  # Landscape for tables
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, txt="Exam Timetable", ln=1, align='C')
    
    col_widths = [20, 40, 50, 30, 30, 30]  # Adjust as needed: Date, Semester, Branch, Subject, Time, Duration
    headers = ['Date', 'Semester', 'Branch', 'Subject', 'Time Slot', 'Duration']
    
    # Print headers
    pdf._row_counter = 0
    print_row_custom(pdf, headers, col_widths, header=True)
    
    # Print data
    for sem, df_sem in sem_dict.items():
        for _, row in df_sem.iterrows():
            row_data = [
                row.get('Exam Date', ''),
                sem,
                row.get('Branch', ''),
                row.get('Subject', ''),
                row.get('Time Slot', ''),
                row.get('Exam Duration', 3)
            ]
            print_row_custom(pdf, row_data, col_widths)
    
    pdf.output(output_path)
