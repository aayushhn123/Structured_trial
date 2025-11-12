# generation.py
import pandas as pd
import streamlit as st
from datetime import datetime
from fpdf import FPDF
import base64
from io import BytesIO
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter


def save_to_excel(df_dict, college_name):
    """Generate main timetable Excel with ORIGINAL formatting."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sem, df in df_dict.items():
            df_out = df.copy()
            df_out['Exam Date'] = df_out['Exam Date'].apply(
                lambda x: datetime.strptime(x, "%d-%m-%Y").strftime("%d-%m-%Y") if pd.notna(x) and x != "" else ""
            )
            df_out = df_out[['Branch', 'Semester', 'Subject', 'ModuleCode', 'StudentCount', 'Exam Date', 'Time Slot']]
            df_out = df_out.sort_values(['Exam Date', 'Time Slot', 'Branch'])
            
            sheet_name = f"Sem {sem}"
            df_out.to_excel(writer, sheet_name=sheet_name, index=False, startrow=2)

            worksheet = writer.sheets[sheet_name]
            
            # HEADER: College Name
            college_header = f"{college_name} - EXAMINATION TIMETABLE"
            worksheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=7)
            top_cell = worksheet.cell(row=1, column=1)
            top_cell.value = college_header
            top_cell.font = Font(name="Arial", size=14, bold=True)
            top_cell.alignment = Alignment(horizontal="center", vertical="center")

            # COLUMN HEADERS
            headers = ['BRANCH', 'SEM', 'SUBJECT', 'MODULE CODE', 'STUDENTS', 'EXAM DATE', 'TIME SLOT']
            for col_num, header in enumerate(headers, 1):
                cell = worksheet.cell(row=3, column=col_num)
                cell.value = header
                cell.font = Font(name="Arial", size=11, bold=True)
                cell.alignment = Alignment(horizontal="center", vertical="center")

            # COLUMN WIDTHS (EXACT ORIGINAL)
            column_widths = [12, 8, 40, 15, 12, 15, 18]
            for i, width in enumerate(column_widths, 1):
                worksheet.column_dimensions[get_column_letter(i)].width = width

            # DATA ROWS
            for row in worksheet[f"A4:G{worksheet.max_row}"]:
                for cell in row:
                    cell.font = Font(name="Arial", size=10)
                    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                    thin = Side(border_style="thin")
                    cell.border = Border(left=thin, right=thin, top=thin, bottom=thin)

            # ALTERNATING ROW COLORS
            for idx, row in enumerate(worksheet[f"A4:G{worksheet.max_row}"], start=4):
                fill_color = "F2F2F2" if idx % 2 == 0 else "FFFFFF"
                fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type="solid")
                for cell in row:
                    cell.fill = fill

    output.seek(0)
    return output


def save_verification_excel(df_dict, college_name):
    """Generate verification Excel (same format as main)."""
    # Identical to save_to_excel — used for verification copy
    return save_to_excel(df_dict, college_name)


def generate_pdf_timetable(df_dict, college_name):
    """Generate PDF timetable with ORIGINAL layout."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"{college_name} - EXAMINATION TIMETABLE", ln=1, align="C")
    pdf.ln(5)

    for sem, df in df_dict.items():
        df_out = df.copy()
        df_out['Exam Date'] = pd.to_datetime(df_out['Exam Date'], format="%d-%m-%Y", errors='coerce')
        df_out = df_out.dropna(subset=['Exam Date'])
        df_out = df_out[['Branch', 'Exam Date', 'Time Slot', 'Subject', 'ModuleCode', 'StudentCount']]
        df_out = df_out.sort_values(['Exam Date', 'Time Slot', 'Branch'])

        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, f"Semester {sem}", ln=1)
        pdf.set_font("Arial", size=10)

        # Table Header
        col_widths = [25, 25, 30, 60, 25, 20]
        headers = ["BRANCH", "DATE", "TIME", "SUBJECT", "CODE", "STUDENTS"]
        for i, (header, width) in enumerate(zip(headers, col_widths)):
            pdf.set_fill_color(200, 200, 200)
            pdf.cell(width, 8, header, border=1, fill=True)
        pdf.ln()

        # Data Rows
        for _, row in df_out.iterrows():
            values = [
                str(row['Branch']),
                row['Exam Date'].strftime("%d-%m-%Y") if pd.notna(row['Exam Date']) else "",
                str(row['Time Slot']),
                str(row['Subject']),
                str(row['ModuleCode']),
                str(int(row['StudentCount'])) if pd.notna(row['StudentCount']) else "0"
            ]
            for i, (value, width) in enumerate(zip(values, col_widths)):
                fill = 1 if i % 2 == 0 else 0
                pdf.set_fill_color(245, 245, 245) if fill else pdf.set_fill_color(255, 255, 255)
                pdf.cell(width, 7, value, border=1, fill=fill)
            pdf.ln()

        pdf.ln(5)

    pdf_output = BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)
    return pdf_output


def create_download_link(file_data, filename, file_type):
    """Create styled download button."""
    b64 = base64.b64encode(file_data.read()).decode()
    file_data.seek(0)
    return f'''
        <a href="data:application/octet-stream;base64,{b64}" download="{filename}">
            <button style="
                background-color: #4CAF50; color: white; padding: 10px 20px;
                text-align: center; text-decoration: none; display: inline-block;
                font-size: 14px; margin: 4px 2px; cursor: pointer; border: none; border-radius: 4px;
            ">
                Download {file_type}
            </button>
        </a>
    '''
