import streamlit as st
import pandas as pd
from datetime import timedelta, date
from utils import get_valid_dates_in_range, find_next_valid_day_in_range, get_preferred_slot, normalize_date_to_ddmmyyyy

def schedule_all_subjects_comprehensively(df, holidays, base_date, end_date, MAX_STUDENTS_PER_SESSION=2000):
    """
    FIXED ZERO-UNSCHEDULED SUPER SCHEDULING WITH CAPACITY CONSTRAINTS
    Now enforces maximum student capacity per time slot (morning/afternoon)
    """
    st.info(f"🚀 SCHEDULING with {MAX_STUDENTS_PER_SESSION} students max per session...")
    
    # STEP 1: COMPREHENSIVE SUBJECT ANALYSIS
    total_subjects_count = len(df)
    
    # Filter eligible subjects (exclude INTD and OE)
    eligible_subjects = df[
        (df['Category'] != 'INTD') & 
        (~(df['OE'].notna() & (df['OE'].str.strip() != "")))
    ].copy()
    
    if eligible_subjects.empty:
        st.info("No eligible subjects to schedule")
        return df
    
    # Helper functions
    def find_next_valid_day(start_date, holidays_set):
        return find_next_valid_day_in_range(start_date, end_date, holidays_set)
    
    # NEW: Track student counts per date and time slot
    session_capacity = {}  # Format: {date_str: {'morning': count, 'afternoon': count}}
    
    def get_session_capacity(date_str, time_slot):
        """Get current student count for a session"""
        if date_str not in session_capacity:
            session_capacity[date_str] = {'morning': 0, 'afternoon': 0}
        
        session_type = 'morning' if '10:00 AM' in time_slot else 'afternoon'
        return session_capacity[date_str][session_type]
    
    def add_to_session_capacity(date_str, time_slot, student_count):
        """Add students to a session's capacity"""
        if date_str not in session_capacity:
            session_capacity[date_str] = {'morning': 0, 'afternoon': 0}
        
        session_type = 'morning' if '10:00 AM' in time_slot else 'afternoon'
        session_capacity[date_str][session_type] += student_count
    
    def can_fit_in_session(date_str, time_slot, student_count):
        """Check if adding these students would exceed capacity"""
        current_capacity = get_session_capacity(date_str, time_slot)
        return (current_capacity + student_count) <= MAX_STUDENTS_PER_SESSION
    
    # STEP 2: CREATE ATOMIC SUBJECT UNITS
    all_branch_sem_combinations = set()
    branch_sem_details = {}
    
    for _, row in eligible_subjects.iterrows():
        branch_sem = f"{row['Branch']}_{row['Semester']}"
        all_branch_sem_combinations.add(branch_sem)
        branch_sem_details[branch_sem] = {
            'branch': row['Branch'],
            'semester': row['Semester'],
            'subbranch': row['SubBranch']
        }
    
    st.write(f"🎯 **Coverage target:** {len(all_branch_sem_combinations)} branch-semester combinations")
    
    # Create ATOMIC SUBJECT UNITS
    atomic_subject_units = {}
    
    for module_code, group in eligible_subjects.groupby('ModuleCode'):
        branch_sem_combinations = []
        unique_branches = set()
        unique_semesters = set()
        
        for _, row in group.iterrows():
            branch_sem = f"{row['Branch']}_{row['Semester']}"
            branch_sem_combinations.append(branch_sem)
            unique_branches.add(row['Branch'])
            unique_semesters.add(row['Semester'])
        
        frequency = len(set(branch_sem_combinations))
        
        is_common_across = group['CommonAcrossSems'].iloc[0] if 'CommonAcrossSems' in group.columns else False
        is_common_within = group['IsCommon'].iloc[0] == 'YES' if 'IsCommon' in group.columns else False
        is_common = is_common_across or is_common_within or frequency > 1
        
        atomic_unit = {
            'module_code': module_code,
            'subject_name': group['Subject'].iloc[0],
            'frequency': frequency,
            'is_common': is_common,
            'is_common_across': is_common_across,
            'is_common_within': is_common_within,
            'branch_sem_combinations': list(set(branch_sem_combinations)),
            'all_rows': list(group.index),
            'group_data': group,
            'scheduled': False,
            'scheduled_date': None,
            'scheduled_slot': None,
            'category': group['Category'].iloc[0] if 'Category' in group.columns else 'UNKNOWN',
            'cross_semester_span': len(unique_semesters) > 1,
            'cross_branch_span': len(unique_branches) > 1,
            'unique_semesters': list(unique_semesters),
            'unique_branches': list(unique_branches)
        }
        
        priority_score = frequency * 10
        
        if is_common_across:
            priority_score += 50
        elif is_common_within:
            priority_score += 25
        elif frequency > 1:
            priority_score += 15
        
        if atomic_unit['cross_semester_span']:
            priority_score += 15
        if atomic_unit['cross_branch_span']:
            priority_score += 10
        
        atomic_unit['priority_score'] = priority_score
        atomic_subject_units[module_code] = atomic_unit
    
    sorted_atomic_units = sorted(atomic_subject_units.values(), key=lambda x: x['priority_score'], reverse=True)
    
    very_high_priority = [unit for unit in sorted_atomic_units if unit['is_common_across'] or unit['frequency'] >= 8]
    high_priority = [unit for unit in sorted_atomic_units if unit['is_common_within'] and unit not in very_high_priority]
    medium_priority = [unit for unit in sorted_atomic_units if unit['frequency'] >= 2 and unit not in very_high_priority and unit not in high_priority]
    low_priority = [unit for unit in sorted_atomic_units if unit not in very_high_priority and unit not in high_priority and unit not in medium_priority]
    
    st.write(f"🎯 **Atomic unit classification:**")
    st.write(f"   🔥 Very High Priority: {len(very_high_priority)} units")
    st.write(f"   📊 High Priority: {len(high_priority)} units")
    st.write(f"   📋 Medium Priority: {len(medium_priority)} units")
    st.write(f"   📄 Low Priority: {len(low_priority)} units")
    
    # STEP 3: ATOMIC SCHEDULING ENGINE WITH CAPACITY CONSTRAINTS
    daily_scheduled_branch_sem = {}
    scheduled_count = 0
    current_date = base_date
    scheduling_day = 0
    target_days = 15
    
    master_queue = very_high_priority + high_priority + medium_priority + low_priority
    unscheduled_units = master_queue.copy()
    
    while scheduling_day < target_days and unscheduled_units:
        exam_date = find_next_valid_day(current_date, holidays)
        if exam_date is None:
            st.warning("⚠️ No more valid exam days available in main scheduling")
            break
        
        date_str = exam_date.strftime("%d-%m-%Y")
        scheduling_day += 1
        
        st.write(f"📅 **Day {scheduling_day} ({date_str})**")
        
        if date_str not in daily_scheduled_branch_sem:
            daily_scheduled_branch_sem[date_str] = set()
        
        day_scheduled_units = []
        units_to_remove = []
        
        # PHASE A: Schedule atomic units with capacity constraints
        for atomic_unit in unscheduled_units:
            conflicts = False
            available_branch_sems = []
            
            for branch_sem in atomic_unit['branch_sem_combinations']:
                if branch_sem in daily_scheduled_branch_sem[date_str]:
                    conflicts = True
                    break
                else:
                    available_branch_sems.append(branch_sem)
            
            if not conflicts and available_branch_sems:
                # Determine time slot
                semester_counts = {}
                for sem in atomic_unit['unique_semesters']:
                    semester_counts[sem] = semester_counts.get(sem, 0) + 1
                
                preferred_semester = max(semester_counts.keys()) if semester_counts else atomic_unit['unique_semesters'][0]
                time_slot = get_preferred_slot(preferred_semester)
                
                # NEW: Calculate total student count for this unit
                total_students = 0
                for row_idx in atomic_unit['all_rows']:
                    student_count = df.loc[row_idx, 'StudentCount']
                    total_students += int(student_count) if pd.notna(student_count) else 0
                
                # NEW: Check if this unit fits in the session capacity
                if not can_fit_in_session(date_str, time_slot, total_students):
                    # Try alternate time slot
                    alternate_slot = "2:00 PM - 5:00 PM" if time_slot == "10:00 AM - 1:00 PM" else "10:00 AM - 1:00 PM"
                    
                    if can_fit_in_session(date_str, alternate_slot, total_students):
                        time_slot = alternate_slot
                        st.write(f"  🔄 Moved to alternate slot due to capacity: {atomic_unit['subject_name']}")
                    else:
                        # Cannot fit today, skip to next unit
                        continue
                
                # Schedule ALL instances of this subject
                unit_scheduled_count = 0
                for row_idx in atomic_unit['all_rows']:
                    df.loc[row_idx, 'Exam Date'] = date_str
                    df.loc[row_idx, 'Time Slot'] = time_slot
                    unit_scheduled_count += 1
                
                # Update tracking
                for branch_sem in atomic_unit['branch_sem_combinations']:
                    daily_scheduled_branch_sem[date_str].add(branch_sem)
                
                # NEW: Update capacity tracking
                add_to_session_capacity(date_str, time_slot, total_students)
                
                atomic_unit['scheduled'] = True
                atomic_unit['scheduled_date'] = date_str
                atomic_unit['scheduled_slot'] = time_slot
                scheduled_count += unit_scheduled_count
                
                day_scheduled_units.append(atomic_unit)
                units_to_remove.append(atomic_unit)
                
                unit_type = "COMMON" if atomic_unit['is_common'] else "INDIVIDUAL"
                st.write(f"  ✅ **{unit_type} ATOMIC:** {atomic_unit['subject_name']} → "
                         f"{len(atomic_unit['branch_sem_combinations'])} branches, "
                         f"{total_students} students at {time_slot}")
                
                # Verify no splitting for common subjects
                if atomic_unit['is_common']:
                    dates_used = set()
                    for row_idx in atomic_unit['all_rows']:
                        exam_date_value = df.loc[row_idx, 'Exam Date']
                        if pd.notna(exam_date_value) and exam_date_value != "":
                            dates_used.add(exam_date_value)
                    
                    if len(dates_used) > 1:
                        st.error(f"❌ CRITICAL ERROR: {atomic_unit['subject_name']} scheduled across {len(dates_used)} dates!")
                    else:
                        st.write(f"    ✅ Common subject integrity verified for {atomic_unit['subject_name']}")
        
        for unit in units_to_remove:
            unscheduled_units.remove(unit)
        
        # PHASE B: Fill gaps with capacity awareness
        remaining_branch_sems = list(all_branch_sem_combinations - daily_scheduled_branch_sem[date_str])
        
        if remaining_branch_sems:
            st.write(f"  🎯 **FILLING GAPS:** {len(remaining_branch_sems)} remaining slots...")
            
            additional_fills = []
            for atomic_unit in unscheduled_units.copy():
                if atomic_unit['frequency'] == 1:
                    unit_branch_sem = atomic_unit['branch_sem_combinations'][0]
                    
                    if unit_branch_sem in remaining_branch_sems:
                        preferred_semester = atomic_unit['unique_semesters'][0]
                        time_slot = get_preferred_slot(preferred_semester)
                        
                        # Check capacity for gap filling
                        total_students = 0
                        for row_idx in atomic_unit['all_rows']:
                            student_count = df.loc[row_idx, 'StudentCount']
                            total_students += int(student_count) if pd.notna(student_count) else 0
                        
                        if not can_fit_in_session(date_str, time_slot, total_students):
                            alternate_slot = "2:00 PM - 5:00 PM" if time_slot == "10:00 AM - 1:00 PM" else "10:00 AM - 1:00 PM"
                            if can_fit_in_session(date_str, alternate_slot, total_students):
                                time_slot = alternate_slot
                            else:
                                continue
                        
                        for row_idx in atomic_unit['all_rows']:
                            df.loc[row_idx, 'Exam Date'] = date_str
                            df.loc[row_idx, 'Time Slot'] = time_slot
                        
                        daily_scheduled_branch_sem[date_str].add(unit_branch_sem)
                        remaining_branch_sems.remove(unit_branch_sem)
                        add_to_session_capacity(date_str, time_slot, total_students)
                        
                        atomic_unit['scheduled'] = True
                        atomic_unit['scheduled_date'] = date_str
                        atomic_unit['scheduled_slot'] = time_slot
                        scheduled_count += len(atomic_unit['all_rows'])
                        
                        additional_fills.append(atomic_unit)
                        st.write(f"    📄 **GAP FILL:** {atomic_unit['subject_name']} ({total_students} students) at {time_slot}")
            
            for unit in additional_fills:
                unscheduled_units.remove(unit)
        
        # Display capacity usage
        morning_capacity = get_session_capacity(date_str, "10:00 AM - 1:00 PM")
        afternoon_capacity = get_session_capacity(date_str, "2:00 PM - 5:00 PM")
        
        st.write(f"  📊 **Session Capacity Usage:**")
        st.write(f"    Morning: {morning_capacity}/{MAX_STUDENTS_PER_SESSION} students ({morning_capacity/MAX_STUDENTS_PER_SESSION*100:.1f}%)")
        st.write(f"    Afternoon: {afternoon_capacity}/{MAX_STUDENTS_PER_SESSION} students ({afternoon_capacity/MAX_STUDENTS_PER_SESSION*100:.1f}%)")
        
        # Daily verification
        final_coverage = len(daily_scheduled_branch_sem[date_str])
        coverage_percent = (final_coverage / len(all_branch_sem_combinations)) * 100
        
        st.write(f"  📊 **Daily Summary:** {len(day_scheduled_units) + len(additional_fills) if 'additional_fills' in locals() else len(day_scheduled_units)} units scheduled, "
                 f"{final_coverage}/{len(all_branch_sem_combinations)} branches covered ({coverage_percent:.1f}%)")
        
        progress_percent = (scheduled_count / len(eligible_subjects)) * 100
        st.write(f"  📈 **Overall progress:** {scheduled_count}/{len(eligible_subjects)} subjects ({progress_percent:.1f}%)")
        
        if not unscheduled_units:
            st.success(f"🎉 **ALL UNITS SCHEDULED IN TARGET PERIOD!** Completed in {scheduling_day} days")
            break
        
        current_date = exam_date + timedelta(days=1)
    
    # STEP 4: EXTENDED SCHEDULING FOR REMAINING UNITS
    if unscheduled_units:
        st.warning(f"⚠️ {len(unscheduled_units)} units still need scheduling - entering extended mode")
        
        extended_day = scheduling_day
        
        while unscheduled_units and extended_day < 25:
            exam_date = find_next_valid_day(current_date, holidays)
            if exam_date is None:
                st.error("❌ No more valid days available")
                break
            
            date_str = exam_date.strftime("%d-%m-%Y")
            extended_day += 1
            
            st.write(f"  📅 **Extended Day {extended_day} ({date_str})**")
            
            if date_str not in daily_scheduled_branch_sem:
                daily_scheduled_branch_sem[date_str] = set()
            
            units_scheduled_today = []
            for atomic_unit in unscheduled_units.copy():
                conflicts = False
                for branch_sem in atomic_unit['branch_sem_combinations']:
                    if branch_sem in daily_scheduled_branch_sem[date_str]:
                        conflicts = True
                        break
                
                if not conflicts:
                    preferred_semester = atomic_unit['unique_semesters'][0]
                    time_slot = get_preferred_slot(preferred_semester)
                    
                    # Check capacity
                    total_students = 0
                    for row_idx in atomic_unit['all_rows']:
                        student_count = df.loc[row_idx, 'StudentCount']
                        total_students += int(student_count) if pd.notna(student_count) else 0
                    
                    if not can_fit_in_session(date_str, time_slot, total_students):
                        alternate_slot = "2:00 PM - 5:00 PM" if time_slot == "10:00 AM - 1:00 PM" else "10:00 AM - 1:00 PM"
                        if can_fit_in_session(date_str, alternate_slot, total_students):
                            time_slot = alternate_slot
                        else:
                            continue
                    
                    for row_idx in atomic_unit['all_rows']:
                        df.loc[row_idx, 'Exam Date'] = date_str
                        df.loc[row_idx, 'Time Slot'] = time_slot
                    
                    for branch_sem in atomic_unit['branch_sem_combinations']:
                        daily_scheduled_branch_sem[date_str].add(branch_sem)
                    
                    add_to_session_capacity(date_str, time_slot, total_students)
                    atomic_unit['scheduled'] = True
                    scheduled_count += len(atomic_unit['all_rows'])
                    units_scheduled_today.append(atomic_unit)
            
            for unit in units_scheduled_today:
                unscheduled_units.remove(unit)
            
            st.write(f"    📄 Extended day scheduled: {len(units_scheduled_today)} units")
            current_date = exam_date + timedelta(days=1)
    
    # STEP 5: FINAL VERIFICATION AND STATISTICS
    st.write("📊 **Step 5:** Final verification and statistics...")
    
    successfully_scheduled = df[
        (df['Exam Date'] != "") & 
        (df['Exam Date'] != "Out of Range") & 
        (df['Category'] != 'INTD') & 
        (~(df['OE'].notna() & (df['OE'].str.strip() != "")))
    ]
    
    split_subjects = 0
    properly_grouped_common = 0
    
    for atomic_unit in atomic_subject_units.values():
        if atomic_unit['is_common'] and atomic_unit['scheduled']:
            dates_used = set()
            for row_idx in atomic_unit['all_rows']:
                exam_date_value = df.loc[row_idx, 'Exam Date']
                if pd.notna(exam_date_value) and exam_date_value != "":
                    dates_used.add(exam_date_value)
            
            if len(dates_used) > 1:
                split_subjects += 1
                st.error(f"❌ SPLIT DETECTED: {atomic_unit['subject_name']} across {len(dates_used)} dates")
            else:
                properly_grouped_common += 1
    
    total_days_used = len(daily_scheduled_branch_sem)
    success_rate = (len(successfully_scheduled) / len(eligible_subjects)) * 100
    
    st.success(f"🏆 **ATOMIC SCHEDULING WITH CAPACITY CONSTRAINTS COMPLETE:**")
    st.write(f"   📚 **Total subjects scheduled:** {len(successfully_scheduled)}/{len(eligible_subjects)} ({success_rate:.1f}%)")
    st.write(f"   📅 **Days used:** {total_days_used}")
    st.write(f"   ✅ **Properly grouped common subjects:** {properly_grouped_common}")
    st.write(f"   ❌ **Split common subjects:** {split_subjects}")
    st.write(f"   👥 **Maximum capacity per session:** {MAX_STUDENTS_PER_SESSION} students")
    
    if split_subjects == 0:
        st.success("🎉 **PERFECT: NO COMMON SUBJECTS SPLIT!**")
        st.balloons()
    else:
        st.error(f"❌ **CRITICAL: {split_subjects} common subjects were split across dates!**")
    
    return df

def validate_capacity_constraints(df_dict, max_capacity=2000):
    """
    Validate that no session exceeds the maximum student capacity
    Returns: (is_valid, violations_list)
    """
    violations = []
    
    all_data = pd.concat(df_dict.values(), ignore_index=True)
    
    # Group by date and time slot
    for (date_str, time_slot), group in all_data.groupby(['Exam Date', 'Time Slot']):
        if pd.isna(date_str) or date_str == "" or date_str == "Out of Range":
            continue
        
        # Calculate total students
        total_students = group['StudentCount'].fillna(0).sum()
        
        if total_students > max_capacity:
            violations.append({
                'date': date_str,
                'time_slot': time_slot,
                'student_count': int(total_students),
                'excess': int(total_students - max_capacity),
                'subjects_count': len(group)
            })
    
    return len(violations) == 0, violations

def schedule_electives_globally(df_ele, max_non_elec_date, holidays_set):
    """
    Schedule electives globally after main scheduling.
    Assumes OE1/OE5 on one day, OE2 on next.
    """
    if df_ele.empty:
        return df_ele
    
    # Find valid days
    elective_day1 = find_next_valid_day_for_electives(
        datetime.combine(max_non_elec_date, datetime.min.time()) + timedelta(days=1), 
        holidays_set
    )
    elective_day2 = find_next_valid_day_for_electives(elective_day1 + timedelta(days=1), holidays_set)
    
    day1_str = elective_day1.strftime("%d-%m-%Y") if elective_day1 else ""
    day2_str = elective_day2.strftime("%d-%m-%Y") if elective_day2 else ""
    
    # Schedule OE1/OE5 on day1, OE2 on day2
    oe1_mask = df_ele['OE'].isin(['OE1', 'OE5'])
    df_ele.loc[oe1_mask, 'Exam Date'] = day1_str
    df_ele.loc[oe1_mask, 'Time Slot'] = "10:00 AM - 1:00 PM"
    
    oe2_mask = df_ele['OE'] == 'OE2'
    df_ele.loc[oe2_mask, 'Exam Date'] = day2_str
    df_ele.loc[oe2_mask, 'Time Slot'] = "2:00 PM - 5:00 PM"
    
    st.success(f"🎓 Electives scheduled: OE1/OE5 on {day1_str}, OE2 on {day2_str}")
    return df_ele

def optimize_schedule_by_filling_gaps(sem_dict, holidays, base_date, end_date):
    """
    Optimize schedule by filling gaps with uncommon subjects.
    """
    if not sem_dict:
        return sem_dict, 0, []
    
    st.info("🎯 Optimizing schedule by filling gaps...")
    
    all_data = pd.concat(sem_dict.values(), ignore_index=True)
    all_data['Exam Date'] = all_data['Exam Date'].apply(normalize_date_to_ddmmyyyy)
    
    # Get all scheduled dates
    scheduled_dates = sorted(all_data[all_data['Exam Date'] != '']['Exam Date'].unique(), 
                             key=lambda x: datetime.strptime(x, "%d-%m-%Y"))
    
    if not scheduled_dates:
        return sem_dict, 0, []
    
    all_scheduled_dates = scheduled_dates
    original_span = (datetime.strptime(all_scheduled_dates[-1], "%d-%m-%Y") - 
                     datetime.strptime(all_scheduled_dates[0], "%d-%m-%Y")).days + 1
    
    # Identify gaps and move uncommon subjects
    moves_made = 0
    optimization_log = []
    
    # Simple gap filling: Move low-priority subjects to earlier empty slots (uncommon only)
    for sem in sem_dict:
        df_sem = sem_dict[sem]
        uncommon = df_sem[(df_sem['CommonAcrossSems'] == False) & (df_sem['IsCommon'] != 'YES')]
        
        for idx, row in uncommon.iterrows():
            current_date = row['Exam Date']
            if current_date == '' or current_date == 'Out of Range':
                continue
            
            # Find earlier empty day
            current_dt = datetime.strptime(current_date, "%d-%m-%Y")
            gap_date = find_next_valid_day_in_range(base_date, current_dt - timedelta(days=1), holidays)
            if gap_date:
                gap_str = gap_date.strftime("%d-%m-%Y")
                # Check if gap is empty for this branch-sem
                mask = (sem_dict[sem]['Exam Date'] == gap_str) & (sem_dict[sem]['Branch'] == row['Branch'])
                if len(sem_dict[sem][mask]) == 0:
                    sem_dict[sem].loc[idx, 'Exam Date'] = gap_str
                    moves_made += 1
                    optimization_log.append(f"Moved {row['Subject']} to {gap_str}")
    
    # Calculate span reduction
    if moves_made > 0:
        updated_all_data = pd.concat(sem_dict.values(), ignore_index=True)
        updated_scheduled = updated_all_data[
            (updated_all_data['Exam Date'] != "") & 
            (updated_all_data['Exam Date'] != "Out of Range")
        ].copy()
        
        if not updated_scheduled.empty:
            updated_scheduled['Exam Date'] = updated_scheduled['Exam Date'].apply(normalize_date_to_ddmmyyyy)
            updated_dates = sorted(updated_scheduled['Exam Date'].unique(), 
                                 key=lambda x: datetime.strptime(x, "%d-%m-%Y"))
            
            if updated_dates:
                new_first_date = updated_dates[0]
                new_last_date = updated_dates[-1]
                
                new_span = (datetime.strptime(new_last_date, "%d-%m-%Y") - 
                           datetime.strptime(new_first_date, "%d-%m-%Y")).days + 1
                
                span_reduction = original_span - new_span
                
                if span_reduction > 0:
                    optimization_log.append(f"Schedule span reduced by {span_reduction} days!")
                    st.success(f"📉 Schedule span reduced from {original_span} to {new_span} days (saved {span_reduction} days)")
    
    # Ensure all dates in df_dict are properly formatted
    for sem in sem_dict:
        sem_dict[sem]['Exam Date'] = sem_dict[sem]['Exam Date'].apply(normalize_date_to_ddmmyyyy)
    
    if moves_made > 0:
        st.success(f"✅ Gap Optimization: Made {moves_made} moves to fill gaps!")
        with st.expander("📋 Gap Optimization Details"):
            for log in optimization_log:
                st.write(f"• {log}")
    else:
        st.info("ℹ️ No beneficial moves found for gap optimization (only uncommon subjects considered)")
    
    return sem_dict, moves_made, optimization_log

def optimize_oe_subjects_after_scheduling(sem_dict, holidays, optimizer=None):
    """
    After main scheduling AND gap optimization, check if OE subjects can be moved to earlier COMPLETELY EMPTY days.
    CRITICAL: OE2 must be scheduled on the day immediately after OE1/OE5.
    UPDATED: Only moves to days with NO exams at all, runs AFTER gap optimization.
    """
    if not sem_dict:
        return sem_dict, 0, []
    
    st.info("🎯 Optimizing Open Elective (OE) placement (after gap optimization)...")
    
    # Combine all data to analyze the schedule
    all_data = pd.concat(sem_dict.values(), ignore_index=True)
    
    # Ensure all dates are in DD-MM-YYYY string format
    all_data['Exam Date'] = all_data['Exam Date'].apply(normalize_date_to_ddmmyyyy)
    
    # Separate OE and non-OE data
    oe_data = all_data[all_data['OE'].notna() & (all_data['OE'].str.strip() != "")]
    non_oe_data = all_data[~(all_data['OE'].notna() & (all_data['OE'].str.strip() != ""))]
    
    if oe_data.empty:
        st.info("No OE subjects to optimize")
        return sem_dict, 0, []
    
    # Build schedule tracking: date -> count of ALL exams (including OE)
    exam_count_per_date = {}
    
    # Count ALL scheduled exams per date
    for _, row in all_data.iterrows():
        if pd.notna(row['Exam Date']) and row['Exam Date'].strip() != "":
            date_str = row['Exam Date']
            if date_str not in exam_count_per_date:
                exam_count_per_date[date_str] = 0
            exam_count_per_date[date_str] += 1
    
    # Find all dates in the schedule
    all_dates = sorted(exam_count_per_date.keys(), 
                      key=lambda x: datetime.strptime(x, "%d-%m-%Y"))
    
    if not all_dates:
        return sem_dict, 0, []
    
    st.write(f"📊 Current schedule has exams on {len(all_dates)} different dates")
    
    # Get the date range from first to last exam
    start_date = datetime.strptime(all_dates[0], "%d-%m-%Y")
    end_date = datetime.strptime(all_dates[-1], "%d-%m-%Y")
    
    # Find COMPLETELY EMPTY days in the schedule range
    completely_empty_days = []
    current_date = start_date
    
    while current_date <= end_date:
        if current_date.weekday() != 6 and current_date.date() not in holidays:
            date_str = current_date.strftime("%d-%m-%Y")
            # Check if this date has NO exams at all
            if date_str not in exam_count_per_date:
                completely_empty_days.append(date_str)
        current_date += timedelta(days=1)
    
    # Sort empty days chronologically
    completely_empty_days.sort(key=lambda x: datetime.strptime(x, "%d-%m-%Y"))
    
    st.write(f"🔍 Found {len(completely_empty_days)} completely empty days for potential OE optimization")
    
    if not completely_empty_days:
        st.info("ℹ️ No completely empty days available for OE optimization")
        return sem_dict, 0, []
    
    # Process OE optimization
    oe_data_copy = oe_data.copy()
    oe1_oe5_data = oe_data_copy[oe_data_copy['OE'].isin(['OE1', 'OE5'])]
    oe2_data = oe_data_copy[oe_data_copy['OE'] == 'OE2']
    
    moves_made = 0
    optimization_log = []
    
    # Process OE1/OE5 together (they should always be on the same date/time)
    if not oe1_oe5_data.empty:
        current_oe1_oe5_date = oe1_oe5_data['Exam Date'].iloc[0]
        current_oe1_oe5_date_obj = datetime.strptime(current_oe1_oe5_date, "%d-%m-%Y")
        
        st.write(f"📅 Current OE1/OE5 date: {current_oe1_oe5_date}")
        
        # Find the earliest completely empty day that comes before current OE1/OE5 date
        best_oe1_oe5_date = None
        best_oe2_date = None
        
        for empty_day in completely_empty_days:
            empty_day_obj = datetime.strptime(empty_day, "%d-%m-%Y")
            
            # Only consider dates earlier than current OE1/OE5 date
            if empty_day_obj >= current_oe1_oe5_date_obj:
                break
            
            # Check if the next day is also completely empty (for OE2)
            next_day = find_next_valid_day_for_electives(empty_day_obj + timedelta(days=1), holidays)
            if next_day:
                next_day_str = next_day.strftime("%d-%m-%Y")
                
                # Check if next day is also completely empty
                if next_day_str in completely_empty_days:
                    best_oe1_oe5_date = empty_day
                    best_oe2_date = next_day_str
                    break
        
        # If we found suitable completely empty days, move OE subjects
        if best_oe1_oe5_date and best_oe2_date:
            days_saved = (current_oe1_oe5_date_obj - datetime.strptime(best_oe1_oe5_date, "%d-%m-%Y")).days
            
            st.write(f"✅ Found optimal placement: OE1/OE5 on {best_oe1_oe5_date}, OE2 on {best_oe2_date}")
            
            # Update all OE1/OE5 exams in semester dictionary
            for idx in oe1_oe5_data.index:
                sem = all_data.at[idx, 'Semester']
                branch = all_data.at[idx, 'Branch']
                subject = all_data.at[idx, 'Subject']
                
                # Update in the semester dictionary
                mask = (sem_dict[sem]['Subject'] == subject) & \
                       (sem_dict[sem]['Branch'] == branch)
                sem_dict[sem].loc[mask, 'Exam Date'] = best_oe1_oe5_date
                sem_dict[sem].loc[mask, 'Time Slot'] = "10:00 AM - 1:00 PM"
            
            # Update all OE2 exams to the day immediately after OE1/OE5
            if not oe2_data.empty:
                for idx in oe2_data.index:
                    sem = all_data.at[idx, 'Semester']
                    branch = all_data.at[idx, 'Branch']
                    subject = all_data.at[idx, 'Subject']
                    
                    # Update in the semester dictionary
                    mask = (sem_dict[sem]['Subject'] == subject) & \
                           (sem_dict[sem]['Branch'] == branch)
                    sem_dict[sem].loc[mask, 'Exam Date'] = best_oe2_date
                    sem_dict[sem].loc[mask, 'Time Slot'] = "2:00 PM - 5:00 PM"
            
            moves_made += 1
            optimization_log.append(
                f"Moved OE1/OE5 from {current_oe1_oe5_date} to {best_oe1_oe5_date} (saved {days_saved} days, completely empty day)"
            )
            if not oe2_data.empty:
                optimization_log.append(
                    f"Moved OE2 to {best_oe2_date} (completely empty day, immediately after OE1/OE5)"
                )
        else:
            st.info("ℹ️ No suitable consecutive completely empty days found for OE optimization")
    
    # Ensure all dates in sem_dict are properly formatted
    for sem in sem_dict:
        sem_dict[sem]['Exam Date'] = sem_dict[sem]['Exam Date'].apply(normalize_date_to_ddmmyyyy)
    
    if moves_made > 0:
        st.success(f"✅ OE Optimization: Moved {moves_made} OE groups to completely empty days!")
        with st.expander("📋 OE Optimization Details"):
            for log in optimization_log:
                st.write(f"• {log}")
    else:
        st.info("ℹ️ OE subjects are already optimally placed or no suitable completely empty days available")
    
    return sem_dict, moves_made, optimization_log
