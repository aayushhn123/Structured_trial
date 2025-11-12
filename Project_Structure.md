# Exam Timetable Generator - Modular Project Structure

## 📁 Project File Organization

```
exam-timetable-generator/
│
├── main.py                    # Main application entry point
├── config.py                  # Configuration and constants
├── session_manager.py         # Session state management
├── ui_components.py           # UI components and display functions
├── data_processing.py         # Data reading and processing utilities
├── scheduling.py              # Core scheduling algorithms
├── file_generation.py         # Excel and PDF generation
├── utils.py                   # Helper utility functions
│
├── requirements.txt           # Python dependencies
├── logo.png                   # NMIMS logo (required)
├── README.md                  # Project documentation
└── .gitignore                # Git ignore file
```

## 📝 File Contents Overview

### 1. **main.py** (✅ Already Created)
- Main application entry point
- Orchestrates the entire workflow
- Handles user interactions and timetable generation process

### 2. **config.py** (✅ Already Created)
- Application configuration
- College list and constants
- CSS styling
- Page setup functions

### 3. **session_manager.py** (✅ Already Created)
- Initializes all session state variables
- Manages application state

### 4. **ui_components.py** (🔨 To Create)
Contains:
- `show_college_selector()` - College selection interface
- `display_header()` - Application header
- `display_sidebar_config()` - Sidebar configuration UI
- `display_statistics()` - Statistics display
- `display_timetable_results()` - Timetable results view

### 5. **data_processing.py** (🔨 To Create)
Contains:
- `read_timetable()` - Excel file reading and parsing
- `get_valid_dates_in_range()` - Date validation utilities
- `convert_semester_to_number()` - Semester conversion
- Data transformation functions

### 6. **scheduling.py** (🔨 To Create)
Contains:
- `schedule_all_subjects_comprehensively()` - Main scheduling algorithm
- `schedule_electives_globally()` - Elective scheduling
- `optimize_schedule_by_filling_gaps()` - Gap optimization
- `optimize_oe_subjects_after_scheduling()` - OE optimization
- `validate_capacity_constraints()` - Capacity validation
- `get_preferred_slot()` - Time slot determination

### 7. **file_generation.py** (🔨 To Create)
Contains:
- `save_to_excel()` - Excel file generation
- `save_verification_excel()` - Verification file generation
- `generate_pdf_timetable()` - PDF generation
- `convert_excel_to_pdf()` - Excel to PDF conversion
- PDF formatting and styling functions

### 8. **utils.py** (🔨 To Create)
Contains:
- `int_to_roman()` - Integer to Roman numeral conversion
- `calculate_end_time()` - Time calculation utilities
- `wrap_text()` - Text wrapping for PDF
- `find_next_valid_day_for_electives()` - Date finding utilities
- Other helper functions

## 🔧 Creating the Remaining Files

### Quick Instructions:

1. **Extract code from original file**: I'll provide each module with the appropriate functions extracted from your original `wt_1.py` file.

2. **Module Dependencies**: Each module will import only what it needs:
   ```python
   # Example from scheduling.py
   from datetime import datetime, timedelta
   import pandas as pd
   import streamlit as st
   from utils import find_next_valid_day_for_electives, get_preferred_slot
   ```

3. **Keep imports clean**: Only import necessary functions between modules.

## 📦 requirements.txt

```txt
streamlit>=1.31.0
pandas>=2.0.0
openpyxl>=3.1.0
fpdf>=1.7.2
PyPDF2>=3.0.0
python-dateutil>=2.8.2
```

## 🚀 Deployment Steps

### 1. Local Testing
```bash
# Clone or create your repository
git clone <your-repo-url>
cd exam-timetable-generator

# Install dependencies
pip install -r requirements.txt

# Run locally
streamlit run main.py
```

### 2. GitHub Setup
```bash
# Initialize git (if not already)
git init
git add .
git commit -m "Initial commit: Modular timetable generator"

# Push to GitHub
git remote add origin <your-github-repo-url>
git push -u origin main
```

### 3. Streamlit Cloud Deployment
1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with GitHub
3. Click "New app"
4. Select your repository
5. Set main file path: `main.py`
6. Click "Deploy"

## 📸 Required Files Checklist

- [x] main.py
- [x] config.py
- [x] session_manager.py
- [ ] ui_components.py
- [ ] data_processing.py
- [ ] scheduling.py
- [ ] file_generation.py
- [ ] utils.py
- [ ] requirements.txt
- [ ] logo.png (your NMIMS logo)
- [ ] README.md
- [ ] .gitignore

## 🎯 Benefits of This Structure

1. **Maintainability**: Each module has a clear responsibility
2. **Scalability**: Easy to add new features in the right module
3. **Testability**: Individual functions can be tested separately
4. **Collaboration**: Multiple developers can work on different modules
5. **GitHub-Ready**: Clean structure for version control
6. **Streamlit-Optimized**: Works seamlessly with Streamlit Cloud

## 🔍 Module Interaction Flow

```
main.py
  ├── config.py (styling, constants)
  ├── session_manager.py (state initialization)
  ├── ui_components.py (display functions)
  │     └── config.py (constants)
  ├── data_processing.py (read Excel)
  │     └── utils.py (helper functions)
  ├── scheduling.py (scheduling algorithms)
  │     └── utils.py (helper functions)
  └── file_generation.py (generate outputs)
        └── utils.py (helper functions)
```

## 📊 Estimated Module Sizes

- **main.py**: ~400 lines
- **config.py**: ~200 lines
- **session_manager.py**: ~50 lines
- **ui_components.py**: ~600 lines
- **data_processing.py**: ~400 lines
- **scheduling.py**: ~800 lines
- **file_generation.py**: ~800 lines
- **utils.py**: ~300 lines

**Total**: ~3,550 lines (from original 3,300+ lines)

The slight increase is due to imports and better code organization.

## 🎓 Next Steps

Would you like me to create the remaining modules? I can generate:
1. `ui_components.py` - All UI display functions
2. `data_processing.py` - Data reading and transformation
3. `scheduling.py` - Core scheduling algorithms
4. `file_generation.py` - Excel and PDF generation
5. `utils.py` - Helper utilities

Just let me know which modules you'd like me to create next!
