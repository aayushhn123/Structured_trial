# generation.py
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import base64
from io import BytesIO
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter


def save_to_excel(df_dict, college_name):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        has_data = False
        for sem, df in df_dict.items():
            df_out = df[df['Exam Date'].notna() & (df['Exam Date'] != "")]
            if df_out.empty:
                continue
            df_out = df_out.copy()
            df_out['Exam Date'] = df_out['Exam Date'].apply(
                lambda x: datetime.strptime(x, "%d-%m-%Y").strftime("%d-%m-%Y")
            )
            df_out = df_out[['Branch', 'Semester', 'Subject', 'ModuleCode', 'StudentCount', 'Exam Date', 'Time Slot']]
            df_out = df_out.sort_values(['Exam Date', 'Time Slot', 'Branch'])

            sheet_name = f"Sem {sem}"
            df_out.to_excel(writer, sheet_name=sheet_name, index=False, startrow=2)
            worksheet = writer.sheets[sheet_name]

            # Header
            header = f"{college_name} - EXAMINATION TIMETABLE"
            worksheet.merge_cells('A1:G1')
            cell = worksheet['A1']
            cell.value = header
            cell.font = Font(name="Arial", size=14, bold=True)
            cell.alignment = Alignment(horizontal="center")

            # Column headers
            headers = ['BRANCH', 'SEM', 'SUBJECT', 'MODULE CODE', 'STUDENTS', 'EXAM DATE', 'TIME SLOT']
            for i, h in enumerate(headers, 1):
                c = worksheet.cell(3, i, h)
                c.font = Font(name="Arial", size=11, bold=True)
                c.alignment = Alignment(horizontal="center")

            # Widths
            widths = [12, 8, 40, 15, 12, 15, 18]
            for i, w in enumerate(widths, 1):
                worksheet.column_dimensions[get_column_letter(i)].width = w

            # Data formatting
            for row in worksheet[f'A4:G{worksheet.max_row}']:
                for cell in row:
                    cell.font = Font(name="Arial", size=10)
                    cell.alignment = Alignment(horizontal="center", wrap_text=True)
                    cell.border = Border(left=Side("thin"), right=Side("thin"), top=Side("thin"), bottom=Side("thin"))

            # Alternating fill
            for idx, row in enumerate(worksheet[f'A4:G{worksheet.max_row}'], 4):
                color = "F2F2F2" if idx % 2 == 0 else "FFFFFF"
                fill = PatternFill(start_color=color, end_color=color, fill_type="solid")
                for cell in row:
                    cell.fill = fill
            has_data = True

        if not has_data:
            df = pd.DataFrame([["NO DATA", "", "", "", "", "", ""]], columns=['Branch', 'Semester', 'Subject', 'ModuleCode', 'StudentCount', 'Exam Date', 'Time Slot'])
            df.to_excel(writer, sheet_name="Sem 1", index=False, startrow=2)
            ws = writer.sheets["Sem 1"]
            ws.merge_cells('A1:G1')
            ws['A1'].value = f"{college_name} - NO EXAMS SCHEDULED"
            ws['A1'].font = Font(name="Arial", size=14, bold=True)
            ws-pc['A1'].alignment = Alignment(horizontal="center")

    output.seek(0)
    return output


def save_verification_excel(df_dict, college_name):
    return save_to_excel(df_dict, college_name.replace("EXAMINATION", "VERIFICATION"))


def generate_pdf_timetable(df_dict, college_name):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"{college_name} - EXAMINATION TIMETABLE", ln=1, align="C")
    pdf.ln(5)

    for sem, df in df_dict.items():
        df_out = df.copy()
        df_out['Exam Date'] = pd.to_datetime(df_out['Exam Date'], format="%d-%m-%Y", errors='coerce')
        df_out = df_out.dropna(subset=['Exam Date'])
        if df_out.empty:
            continue
        df_out = df_out[['Branch', 'Exam Date', 'Time Slot', 'Subject', 'ModuleCode', 'StudentCount']]
        df_out = df_out.sort_values(['Exam Date', 'Time Slot', 'Branch'])

        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, f"Semester {sem}", ln=1)
        pdf.set_font("Arial", size=10)

        widths = [25, 25, 30, 60, 25, 20]
        headers = ["BRANCH", "DATE", "TIME", "SUBJECT", "CODE", "STUDENTS"]
        for w, h in zip(widths, headers):
            pdf.cell(w, 8, h, border=1, fill=True)
        pdf.ln()

        for _, r in df_out.iterrows():
            vals = [
                str(r['Branch']),
                r['Exam Date'].strftime("%d-%m-%Y"),
                str(r['Time Slot']),
                str(r['Subject']),
                str(r['ModuleCode']),
                str(int(r['StudentCount']))
            ]
            for i, (v, w) in enumerate(zip(vals, widths)):
                pdf.cell(w, 7, v, border=1, fill=(i%2==0))
            pdf.ln()
        pdf.ln(5)

    out = BytesIO()
    pdf.output(out)
    out.seek(0)
    return out


def create_download_link(file_data, filename, label):
    b64 = base64.b64encode(file_data.read()).decode()
    file_data.seek(0)
    return f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}"><button style="background:#4CAF50;color:white;padding:10px 20px;border:none;border-radius:4px;cursor:pointer;">Download {label}</button></a>'
