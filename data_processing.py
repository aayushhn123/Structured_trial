import pandas as pd
import streamlit as st
import numpy as np
from datetime import datetime

def read_timetable(uploaded_file):
    try:
        df = pd.read_excel(uploaded_file, engine='openpyxl')
        
        # Debug: Show actual column names from the Excel file
        st.write("📋 **Actual columns in uploaded file:**")
        st.write(list(df.columns))
        
        # Enhanced column mapping to handle more variations
        column_mapping = {
            "Program": "Program",
            "Programme": "Program",  # Alternative spelling
            "Stream": "Stream", 
            "Specialization": "Stream",  # Alternative name
            "Branch": "Stream",  # Some files might use Branch for Stream
            "Current Session": "Semester",
            "Academic Session": "Semester",
            "Session": "Semester",
            "Module Description": "SubjectName",
            "Subject Name": "SubjectName",
            "Subject Description": "SubjectName",
            "Module Abbreviation": "ModuleCode",
            "Module Code": "ModuleCode",
            "Subject Code": "ModuleCode",
            "Code": "ModuleCode",
            "Campus Name": "Campus",
            "Campus": "Campus",
            "Difficulty Score": "Difficulty",
            "Difficulty": "Difficulty",
            "Exam Duration": "Exam Duration",
            "Duration": "Exam Duration",
            "Student count": "StudentCount",
            "Student Count": "StudentCount",
            "Enrollment": "StudentCount",
            "Count": "StudentCount",
            "Common across sems": "CommonAcrossSems",
            "Common Across Sems": "CommonAcrossSems",
            "Cross Semester": "CommonAcrossSems",
            "Common Across Semesters": "CommonAcrossSems",
            # NEW: CM Group column variations
            "CM group": "CMGroup",
            "CM Group": "CMGroup",
            "cm group": "CMGroup",
            "CMGroup": "CMGroup",
            "CM_Group": "CMGroup",
            "Common Module Group": "CMGroup",
            # NEW: Exam Slot Number column variations
            "Exam Slot Number": "ExamSlotNumber",
            "exam slot number": "ExamSlotNumber",
            "ExamSlotNumber": "ExamSlotNumber",
            "Exam_Slot_Number": "ExamSlotNumber",
            "Slot Number": "ExamSlotNumber",
            "SlotNumber": "ExamSlotNumber",
            "Exam Slot": "ExamSlotNumber"
        }
        
        # Handle the "Is Common" column with flexible naming
        is_common_variations = ["Is Common", "IsCommon", "is common", "Is_Common", "is_common", "Common"]
        for variation in is_common_variations:
            if variation in df.columns:
                column_mapping[variation] = "IsCommon"
                st.write(f"✅ Found 'Is Common' column as: '{variation}'")
                break
        else:
            st.warning("⚠️ 'Is Common' column not found in uploaded file. Will create default values.")
        
        # Apply the column mapping
        df = df.rename(columns=column_mapping)
        
        # CRITICAL FIX: Handle data type conversion issues
        
        # 1. Fix CommonAcrossSems column - handle float NaN values
        if "CommonAcrossSems" in df.columns:
            # Convert float values to boolean, treating NaN as False
            df["CommonAcrossSems"] = df["CommonAcrossSems"].fillna(False)
            if df["CommonAcrossSems"].dtype == 'float64':
                df["CommonAcrossSems"] = df["CommonAcrossSems"].astype(bool)
        else:
            df["CommonAcrossSems"] = False
        
        # 2. Fix OE column - handle float NaN values
        if "OE" in df.columns:
            # Convert float NaN to empty string for consistency
            df["OE"] = df["OE"].fillna("")
            df["OE"] = df["OE"].astype(str).replace('nan', '')
        else:
            df["OE"] = ""
        
        # NEW: Handle CMGroup column - allow empty values
        if "CMGroup" in df.columns:
            # Convert NaN to empty string, keep as string
            df["CMGroup"] = df["CMGroup"].fillna("")
            df["CMGroup"] = df["CMGroup"].astype(str).replace('nan', '').str.strip()
        else:
            # Create empty column if not present
            df["CMGroup"] = ""
            st.info("ℹ️ 'CM Group' column not found - created empty column")
        
        # NEW: Handle ExamSlotNumber column
        if "ExamSlotNumber" in df.columns:
            # Convert to numeric, treating NaN as 0 or empty
            df["ExamSlotNumber"] = pd.to_numeric(df["ExamSlotNumber"], errors='coerce').fillna(0).astype(int)
        else:
            # Create column with default value 0 if not present
            df["ExamSlotNumber"] = 0
            st.info("ℹ️ 'Exam Slot Number' column not found - created with default value 0")
        
        # 3. Fix numeric columns that might be float
        numeric_columns = ["Exam Duration", "StudentCount", "Difficulty"]
        for col in numeric_columns:
            if col in df.columns:
                df[col] = df[col].fillna(0 if col != "Exam Duration" else 3)
                if col == "Exam Duration":
                    df[col] = df[col].astype(float)
                else:
                    df[col] = df[col].astype(int)
        
        # 4. Ensure string columns are properly handled
        string_columns = ["Program", "Stream", "SubjectName", "ModuleCode", "Campus"]
        for col in string_columns:
            if col in df.columns:
                df[col] = df[col].fillna("").astype(str)
        
        def convert_sem(sem):
            if pd.isna(sem):
                return 0
            
            sem_str = str(sem).strip()
            
            # Handle different semester formats including DIPLOMA and M TECH
            semester_mappings = {
                "Sem I": 1, "Sem II": 2, "Sem III": 3, "Sem IV": 4,
                "Sem V": 5, "Sem VI": 6, "Sem VII": 7, "Sem VIII": 8,
                "Sem IX": 9, "Sem X": 10, "Sem XI": 11, "Sem XII": 12,
                # DIPLOMA variations
                "DIPLOMA Sem I": 1, "DIPLOMA Sem II": 2, "DIPLOMA Sem III": 3,
                "DIPLOMA Sem IV": 4, "DIPLOMA Sem V": 5, "DIPLOMA Sem VI": 6,
                # M TECH variations  
                "M TECH Sem I": 1, "M TECH Sem II": 2, "M TECH Sem III": 3, "M TECH Sem IV": 4,
                # Direct numeric
                "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, 
                "9": 9, "10": 10, "11": 11, "12": 12,
                # Handle Law school specific formats
                "1.0": 1, "2.0": 2, "3.0": 3, "4.0": 4, "5.0": 5, "6.0": 6
            }
            
            return semester_mappings.get(sem_str, 0)

        df["Semester"] = df["Semester"].apply(convert_sem).astype(int)
        
        # Create enhanced branch identifier that considers program type
        def create_branch_identifier(row):
            program = str(row.get("Program", "")).strip()
            stream = str(row.get("Stream", "")).strip()
            
            # Handle cases where stream might be empty or same as program
            if not stream or stream == "nan" or stream == program:
                return program
            else:
                return f"{program}-{stream}"
        
        df["Branch"] = df.apply(create_branch_identifier, axis=1)
        df["Subject"] = df["SubjectName"].astype(str) + " - (" + df["ModuleCode"].astype(str) + ")"
        
        # FIXED: Handle Difficulty assignment more carefully
        if "Category" in df.columns and "Difficulty" in df.columns:
            comp_mask = (df["Category"] == "COMP") & df["Difficulty"].notna()
            # Only keep difficulty for COMP subjects, set others to None
            df.loc[~comp_mask, "Difficulty"] = None
        else:
            df["Difficulty"] = None
        
        df["Exam Date"] = ""
        df["Time Slot"] = ""
        
        # CRITICAL FIX: Ensure proper data type handling for all columns
        df["Exam Duration"] = df["Exam Duration"].fillna(3).astype(float)
        df["StudentCount"] = df["StudentCount"].fillna(0).astype(int)
        df["CommonAcrossSems"] = df["CommonAcrossSems"].fillna(False).astype(bool)
        
        # Handle IsCommon column - create if it doesn't exist
        if "IsCommon" not in df.columns:
            st.info("ℹ️ Creating 'IsCommon' column with enhanced logic for all program types")
            df["IsCommon"] = "NO"  # Default value
            
            # Set YES for subjects that are common across semesters
            df.loc[df["CommonAcrossSems"] == True, "IsCommon"] = "YES"
            
            # Enhanced logic to check for subjects common within semester across different programs
            for (semester, module_code), group in df.groupby(['Semester', 'ModuleCode']):
                unique_branches = group['Branch'].unique()
                unique_programs = group['Program'].unique() if 'Program' in group.columns else []
                
                # If subject appears in multiple branches or programs within same semester
                if len(unique_branches) > 1 or len(unique_programs) > 1:
                    df.loc[group.index, "IsCommon"] = "YES"
        else:
            # Clean up the IsCommon column values
            df["IsCommon"] = df["IsCommon"].astype(str).str.strip().str.upper()
            df["IsCommon"] = df["IsCommon"].replace({"TRUE": "YES", "FALSE": "NO", "1": "YES", "0": "NO"})
            df["IsCommon"] = df["IsCommon"].fillna("NO")
        
        # CRITICAL FIX: Filter out rows with missing essential data
        # Remove rows where essential columns are null/empty
        essential_columns = ["Program", "Semester", "ModuleCode", "SubjectName"]
        initial_count = len(df)
        
        for col in essential_columns:
            if col in df.columns:
                df = df[df[col].notna() & (df[col].astype(str).str.strip() != "")]
        
        final_count = len(df)
        if final_count < initial_count:
            st.warning(f"⚠️ Removed {initial_count - final_count} rows with missing essential data")
        
        if df.empty:
            st.error("❌ No valid data remaining after filtering")
            return None, None, None
        
        df_non = df[df["Category"] != "INTD"].copy()
        df_ele = df[df["Category"] == "INTD"].copy()
        
        def split_br(b):
            p = str(b).split("-", 1)
            if len(p) == 1:
                # Single program case (like DIPLOMA, M TECH without stream)
                return pd.Series([p[0].strip(), ""])
            else:
                return pd.Series([p[0].strip(), p[1].strip()])
        
        # CRITICAL FIX: Handle the split_br operation more carefully
        try:
            for d in (df_non, df_ele):
                if not d.empty:
                    split_result = d["Branch"].apply(split_br)
                    # Ensure we have exactly 2 columns
                    if len(split_result.columns) >= 2:
                        d[["MainBranch", "SubBranch"]] = split_result.iloc[:, :2]
                    else:
                        # Fallback if split doesn't work as expected
                        d["MainBranch"] = d["Branch"]
                        d["SubBranch"] = ""
        except Exception as e:
            st.warning(f"⚠️ Issue with branch splitting: {e}. Using fallback method.")
            for d in (df_non, df_ele):
                if not d.empty:
                    d["MainBranch"] = d["Branch"]
                    d["SubBranch"] = ""
        
        # UPDATED: Include new columns in the output
        cols = ["MainBranch", "SubBranch", "Branch", "Semester", "Subject", "Category", "OE", "Exam Date", "Time Slot",
                "Difficulty", "Exam Duration", "StudentCount", "CommonAcrossSems", "ModuleCode", "IsCommon", "Program",
                "CMGroup", "ExamSlotNumber"]  # Added new columns
        
        # Ensure all required columns exist before selecting
        available_cols = [col for col in cols if col in df_non.columns]
        missing_cols = [col for col in cols if col not in df_non.columns]
        
        if missing_cols:
            st.warning(f"⚠️ Missing columns: {missing_cols}")
            # Add missing columns with default values
            for missing_col in missing_cols:
                if missing_col == "Program":
                    df_non[missing_col] = "B TECH"  # Default program
                    if not df_ele.empty:
                        df_ele[missing_col] = "B TECH"
                elif missing_col == "CMGroup":
                    df_non[missing_col] = ""  # Empty string for CM Group
                    if not df_ele.empty:
                        df_ele[missing_col] = ""
                elif missing_col == "ExamSlotNumber":
                    df_non[missing_col] = 0  # Default value 0
                    if not df_ele.empty:
                        df_ele[missing_col] = 0
                else:
                    df_non[missing_col] = None
                    if not df_ele.empty:
                        df_ele[missing_col] = None
        
        # Update available_cols after adding missing columns
        available_cols = [col for col in cols if col in df_non.columns]
        
        # STORE ORIGINAL DATA FOR FILTER OPTIONS
        st.session_state.original_data_df = df.copy()
        
        # Show summary of new columns
        cm_group_count = len(df[df["CMGroup"].str.strip() != ""]) if "CMGroup" in df.columns else 0
        if cm_group_count > 0:
            st.info(f"✅ Found {cm_group_count} subjects with CM Group assignments")
        
        exam_slot_count = len(df[df["ExamSlotNumber"] > 0]) if "ExamSlotNumber" in df.columns else 0
        if exam_slot_count > 0:
            st.info(f"✅ Found {exam_slot_count} subjects with Exam Slot Number assignments")
        
        return df_non[available_cols], df_ele[available_cols] if not df_ele.empty and available_cols else df_ele, df
        
    except Exception as e:
        st.error(f"Error reading the Excel file: {str(e)}")
        st.error(f"Error details: {type(e).__name__}")
        import traceback
        st.error(f"Full traceback: {traceback.format_exc()}")
        return None, None, None
