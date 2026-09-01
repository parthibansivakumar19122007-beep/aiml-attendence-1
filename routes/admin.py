import os
import uuid
from datetime import datetime
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, session, current_app, jsonify)
from werkzeug.utils import secure_filename
from models import db, User, Student, Faculty, Subject, ClassRoom, Section, Timetable, FaceEmbedding, AuditLog, AttendanceRecord, AttendanceSession, FacultyAttendance
from services.auth_service import login_required, role_required
from services.face_service import enroll_face_from_file, allowed_photo, face_recognition_status

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# ── Helpers ───────────────────────────────────────────────────────────────────
def _audit(action: str, details: str, user_id: int = None):
    try:
        log = AuditLog(
            user_id=user_id or session.get('user_id'),
            action=action,
            details=details,
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()

def _upload_dir():
    return os.path.join(current_app.root_path, 'static', 'uploads')

# ── Dashboard ─────────────────────────────────────────────────────────────────
@admin_bp.route('/dashboard')
@login_required
@role_required('ADMIN')
def dashboard():
    total_students = Student.query.count()
    total_faculty = Faculty.query.count()
    total_subjects = Subject.query.count()
    total_timetable = Timetable.query.count()
    recent_logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(15).all()
    students = Student.query.all()
    faculty_list = Faculty.query.all()
    subjects = Subject.query.filter_by(is_active=True).all()
    face_status = face_recognition_status()
    return render_template(
        'admin/dashboard.html',
        total_students=total_students,
        total_faculty=total_faculty,
        total_subjects=total_subjects,
        total_timetable=total_timetable,
        recent_logs=recent_logs,
        students=students,
        faculty_list=faculty_list,
        subjects=subjects,
        face_status=face_status
    )

# ═══════════════════════════════════════════════════════════════════════════════
# STUDENT MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════
@admin_bp.route('/students')
@login_required
@role_required('ADMIN')
def students():
    all_students = Student.query.all()
    classes = ClassRoom.query.all()
    face_status = face_recognition_status()
    return render_template('admin/students.html',
                           students=all_students,
                           classes=classes,
                           face_status=face_status)

@admin_bp.route('/students/add', methods=['GET', 'POST'])
@login_required
@role_required('ADMIN')
def add_student():
    classes = ClassRoom.query.all()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        student_id = request.form.get('student_id', '').strip().upper()
        password = request.form.get('password', '').strip()
        class_id = request.form.get('class_id', type=int)
        year = request.form.get('year', 1, type=int)
        section = request.form.get('section', 'A').strip().upper()

        username = request.form.get('username', '').strip() or student_id.lower()
        department = request.form.get('department', 'CSE-AIML').strip()

        # Validate required
        if not all([name, email, student_id, password, class_id, username]):
            flash('All fields including Username are required.', 'danger')
            return render_template('admin/add_student.html', classes=classes)

        # Duplicate checks
        if User.query.filter_by(username=username).first():
            flash(f'Username "{username}" is already taken.', 'danger')
            return render_template('admin/add_student.html', classes=classes)
        if User.query.filter_by(email=email).first():
            flash(f'Email "{email}" is already registered.', 'danger')
            return render_template('admin/add_student.html', classes=classes)
        if Student.query.filter_by(student_id=student_id).first():
            flash(f'Student ID "{student_id}" is already taken.', 'danger')
            return render_template('admin/add_student.html', classes=classes)

        # Handle photo upload
        photo_path = None
        photo_file = request.files.get('photo')
        if photo_file and photo_file.filename:
            if not allowed_photo(photo_file.filename):
                flash('Invalid photo format. Use JPG, PNG, or WebP.', 'danger')
                return render_template('admin/add_student.html', classes=classes)
            ext = photo_file.filename.rsplit('.', 1)[1].lower()
            filename = secure_filename(f"{student_id}.{ext}")
            save_dir = os.path.join(_upload_dir(), 'students')
            os.makedirs(save_dir, exist_ok=True)
            save_path = os.path.join(save_dir, filename)
            photo_file.save(save_path)
            photo_path = f'uploads/students/{filename}'

        try:
            u = User(role='STUDENT', name=name, email=email, username=username, department=department, is_active=True, status='ACTIVE')
            u.set_password(password)
            db.session.add(u)
            db.session.flush()

            st = Student(user_id=u.id, student_id=student_id,
                         class_id=class_id, year=year, section=section,
                         photo_path=photo_path)
            db.session.add(st)
            db.session.commit()

            _audit('ADMIN_ADDED_STUDENT', f'Admin added student {student_id} ({name})')
            flash(f'Student {name} ({student_id}) added successfully!', 'success')
            return redirect(url_for('admin.students'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding student: {str(e)}', 'danger')

    return render_template('admin/add_student.html', classes=classes)

@admin_bp.route('/students/<int:student_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('ADMIN')
def edit_student(student_id):
    st = Student.query.get_or_404(student_id)
    classes = ClassRoom.query.all()
    if request.method == 'POST':
        st.user.name = request.form.get('name', st.user.name).strip()
        new_uname = request.form.get('username', '').strip()
        if new_uname and new_uname != st.user.username:
            existing = User.query.filter_by(username=new_uname).first()
            if existing:
                flash(f'Username "{new_uname}" is already taken.', 'danger')
                return render_template('admin/edit_student.html', st=st, classes=classes)
            st.user.username = new_uname
            
        new_email = request.form.get('email', '').strip().lower()
        if new_email and new_email != st.user.email:
            existing_email = User.query.filter_by(email=new_email).first()
            if existing_email:
                flash(f'Email "{new_email}" is already registered.', 'danger')
                return render_template('admin/edit_student.html', st=st, classes=classes)
            st.user.email = new_email

        new_dept = request.form.get('department', '').strip()
        if new_dept:
            st.user.department = new_dept

        new_pass = request.form.get('password', '').strip()
        if new_pass:
            st.user.set_password(new_pass)

        st.year = request.form.get('year', st.year, type=int)
        st.section = request.form.get('section', st.section).strip().upper()
        new_class_id = request.form.get('class_id', type=int)
        if new_class_id:
            st.class_id = new_class_id
        is_active = request.form.get('is_active') == 'on'
        st.user.is_active = is_active
        st.user.status = 'ACTIVE' if is_active else 'INACTIVE'

        photo_file = request.files.get('photo')
        if photo_file and photo_file.filename:
            if allowed_photo(photo_file.filename):
                ext = photo_file.filename.rsplit('.', 1)[1].lower()
                filename = secure_filename(f"{st.student_id}.{ext}")
                save_dir = os.path.join(_upload_dir(), 'students')
                os.makedirs(save_dir, exist_ok=True)
                photo_file.save(os.path.join(save_dir, filename))
                st.photo_path = f'uploads/students/{filename}'

        try:
            db.session.commit()
            _audit('ADMIN_EDITED_STUDENT', f'Admin edited student {st.student_id}')
            flash(f'Student {st.user.name} updated.', 'success')
            return redirect(url_for('admin.students'))
        except Exception as e:
            db.session.rollback()
            flash(f'Update failed: {str(e)}', 'danger')

    return render_template('admin/edit_student.html', st=st, classes=classes)

@admin_bp.route('/students/<int:student_id>/toggle', methods=['POST'])
@admin_bp.route('/students/<int:student_id>/deactivate', methods=['POST'])
@login_required
@role_required('ADMIN')
def toggle_student(student_id):
    st = Student.query.get_or_404(student_id)
    st.user.is_active = not st.user.is_active
    db.session.commit()
    status_str = "activated" if st.user.is_active else "deactivated"
    _audit('ADMIN_TOGGLED_STUDENT', f'{status_str.capitalize()} student {st.student_id}')
    flash(f'Student {st.user.name} {status_str}.', 'info')
    return redirect(url_for('admin.students'))

@admin_bp.route('/students/<int:student_id>/delete', methods=['POST'])
@login_required
@role_required('ADMIN')
def delete_student(student_id):
    st = Student.query.get_or_404(student_id)
    name = st.user.name if st.user else st.student_id
    roll = st.student_id
    user = st.user
    
    try:
        AttendanceRecord.query.filter_by(student_id=st.id).delete()
        if user:
            FaceEmbedding.query.filter_by(user_id=user.id).delete()
        db.session.delete(st)
        if user:
            db.session.delete(user)
        db.session.commit()
        _audit('ADMIN_DELETED_STUDENT', f'Deleted student {roll} ({name})')
        flash(f'Student {name} ({roll}) deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting student: {str(e)}', 'danger')

    return redirect(url_for('admin.students'))


@admin_bp.route('/students/<int:student_id>/enroll-face', methods=['GET', 'POST'])
@login_required
@role_required('ADMIN')
def enroll_student_face(student_id):
    """Enroll or re-enroll a student's face from uploaded photo."""
    st = Student.query.get_or_404(student_id)
    face_status = face_recognition_status()

    if request.method == 'POST':
        photo_file = request.files.get('photo')
        if not photo_file or not photo_file.filename:
            flash('Please upload a photo to enroll face.', 'danger')
            return render_template('admin/enroll_face.html', person=st, role='STUDENT', face_status=face_status)

        if not allowed_photo(photo_file.filename):
            flash('Invalid photo format. Use JPG, PNG, or WebP.', 'danger')
            return render_template('admin/enroll_face.html', person=st, role='STUDENT', face_status=face_status)

        file_bytes = photo_file.read()
        if len(file_bytes) > 5 * 1024 * 1024:
            flash('Photo too large. Maximum size is 5 MB.', 'danger')
            return render_template('admin/enroll_face.html', person=st, role='STUDENT', face_status=face_status)

        # Save photo
        ext = photo_file.filename.rsplit('.', 1)[1].lower()
        filename = secure_filename(f"{st.student_id}_enroll.{ext}")
        save_dir = os.path.join(_upload_dir(), 'students')
        os.makedirs(save_dir, exist_ok=True)
        with open(os.path.join(save_dir, filename), 'wb') as f:
            f.write(file_bytes)
        if not st.photo_path:
            st.photo_path = f'uploads/students/{filename}'

        # Generate embedding
        embedding, error = enroll_face_from_file(file_bytes)
        if error:
            flash(f'Face enrollment failed: {error}', 'danger')
            return render_template('admin/enroll_face.html', person=st, role='STUDENT', face_status=face_status)

        # Deactivate old embeddings
        FaceEmbedding.query.filter_by(user_id=st.user_id, is_active=True).update({'is_active': False})
        # Save new embedding
        new_emb = FaceEmbedding(
            user_id=st.user_id,
            embedding_data=embedding,
            model_name=face_status.get('model', 'opencv_dnn_v1'),
            is_active=True
        )
        db.session.add(new_emb)
        db.session.commit()
        _audit('ADMIN_ENROLLED_STUDENT_FACE', f'Face enrolled for student {st.student_id}')
        flash(f'Face successfully enrolled for {st.user.name}!', 'success')
        return redirect(url_for('admin.students'))

    return render_template('admin/enroll_face.html', person=st, role='STUDENT', face_status=face_status)


# ═══════════════════════════════════════════════════════════════════════════════
# FACULTY MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════
@admin_bp.route('/faculty')
@login_required
@role_required('ADMIN')
def faculty():
    all_faculty = Faculty.query.all()
    classes = ClassRoom.query.all()
    face_status = face_recognition_status()
    return render_template('admin/faculty.html',
                           faculty_list=all_faculty,
                           classes=classes,
                           face_status=face_status)

@admin_bp.route('/faculty/add', methods=['GET', 'POST'])
@login_required
@role_required('ADMIN')
def add_faculty():
    classes = ClassRoom.query.all()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        faculty_id = request.form.get('faculty_id', '').strip().upper()
        password = request.form.get('password', '').strip()
        designation = request.form.get('designation', 'Assistant Professor').strip()

        if not all([name, email, faculty_id, password]):
            flash('All required fields must be filled.', 'danger')
            return render_template('admin/add_faculty.html', classes=classes)

        if User.query.filter_by(email=email).first():
            flash(f'Email "{email}" is already registered.', 'danger')
            return render_template('admin/add_faculty.html', classes=classes)
        if Faculty.query.filter_by(faculty_id=faculty_id).first():
            flash(f'Faculty ID "{faculty_id}" is already taken.', 'danger')
            return render_template('admin/add_faculty.html', classes=classes)

        # Get first department
        from models import Department
        dept = Department.query.first()
        if not dept:
            flash('No department found. Please seed the database first.', 'danger')
            return render_template('admin/add_faculty.html', classes=classes)

        photo_path = None
        photo_file = request.files.get('photo')
        if photo_file and photo_file.filename:
            if not allowed_photo(photo_file.filename):
                flash('Invalid photo format.', 'danger')
                return render_template('admin/add_faculty.html', classes=classes)
            ext = photo_file.filename.rsplit('.', 1)[1].lower()
            filename = secure_filename(f"{faculty_id}.{ext}")
            save_dir = os.path.join(_upload_dir(), 'faculty')
            os.makedirs(save_dir, exist_ok=True)
            photo_file.save(os.path.join(save_dir, filename))
            photo_path = f'uploads/faculty/{filename}'

        try:
            u = User(role='FACULTY', name=name, email=email, username=username, department=department, is_active=True, status='ACTIVE')
            u.set_password(password)
            db.session.add(u)
            db.session.flush()

            f = Faculty(user_id=u.id, faculty_id=faculty_id,
                        department_id=dept.id, designation=designation,
                        photo_path=photo_path)
            db.session.add(f)
            db.session.commit()

            _audit('ADMIN_ADDED_FACULTY', f'Admin added faculty {faculty_id} ({name})')
            flash(f'Faculty {name} ({faculty_id}) added successfully!', 'success')
            return redirect(url_for('admin.faculty'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding faculty: {str(e)}', 'danger')

    return render_template('admin/add_faculty.html', classes=classes)

@admin_bp.route('/faculty/<int:faculty_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('ADMIN')
def edit_faculty(faculty_id):
    f = Faculty.query.get_or_404(faculty_id)
    if request.method == 'POST':
        f.user.name = request.form.get('name', f.user.name).strip()
        
        new_uname = request.form.get('username', '').strip()
        if new_uname and new_uname != f.user.username:
            existing = User.query.filter_by(username=new_uname).first()
            if existing:
                flash(f'Username "{new_uname}" is already taken.', 'danger')
                return render_template('admin/edit_faculty.html', f=f)
            f.user.username = new_uname

        new_email = request.form.get('email', '').strip().lower()
        if new_email and new_email != f.user.email:
            existing_email = User.query.filter_by(email=new_email).first()
            if existing_email:
                flash(f'Email "{new_email}" is already registered.', 'danger')
                return render_template('admin/edit_faculty.html', f=f)
            f.user.email = new_email

        new_dept = request.form.get('department', '').strip()
        if new_dept:
            f.user.department = new_dept

        new_pass = request.form.get('password', '').strip()
        if new_pass:
            f.user.set_password(new_pass)

        f.designation = request.form.get('designation', f.designation).strip()
        is_active = request.form.get('is_active') == 'on'
        f.user.is_active = is_active
        f.user.status = 'ACTIVE' if is_active else 'INACTIVE'

        photo_file = request.files.get('photo')
        if photo_file and photo_file.filename:
            if allowed_photo(photo_file.filename):
                ext = photo_file.filename.rsplit('.', 1)[1].lower()
                filename = secure_filename(f"{f.faculty_id}.{ext}")
                save_dir = os.path.join(_upload_dir(), 'faculty')
                os.makedirs(save_dir, exist_ok=True)
                photo_file.save(os.path.join(save_dir, filename))
                f.photo_path = f'uploads/faculty/{filename}'

        try:
            db.session.commit()
            _audit('ADMIN_EDITED_FACULTY', f'Admin edited faculty {f.faculty_id}')
            flash(f'Faculty {f.user.name} updated.', 'success')
            return redirect(url_for('admin.faculty'))
        except Exception as e:
            db.session.rollback()
            flash(f'Update failed: {str(e)}', 'danger')

    return render_template('admin/edit_faculty.html', f=f)

@admin_bp.route('/faculty/<int:faculty_id>/toggle', methods=['POST'])
@admin_bp.route('/faculty/<int:faculty_id>/deactivate', methods=['POST'])
@login_required
@role_required('ADMIN')
def toggle_faculty(faculty_id):
    f = Faculty.query.get_or_404(faculty_id)
    f.user.is_active = not f.user.is_active
    db.session.commit()
    status_str = "activated" if f.user.is_active else "deactivated"
    _audit('ADMIN_TOGGLED_FACULTY', f'{status_str.capitalize()} faculty {f.faculty_id}')
    flash(f'Faculty {f.user.name} {status_str}.', 'info')
    return redirect(url_for('admin.faculty'))

@admin_bp.route('/faculty/<int:faculty_id>/delete', methods=['POST'])
@login_required
@role_required('ADMIN')
def delete_faculty(faculty_id):
    f = Faculty.query.get_or_404(faculty_id)
    name = f.user.name if f.user else f.faculty_id
    fid = f.faculty_id
    user = f.user
    
    try:
        Timetable.query.filter_by(faculty_id=f.id).delete()
        FacultyAttendance.query.filter_by(faculty_id=f.id).delete()
        AttendanceSession.query.filter_by(faculty_id=f.id).delete()
        if user:
            FaceEmbedding.query.filter_by(user_id=user.id).delete()
        db.session.delete(f)
        if user:
            db.session.delete(user)
        db.session.commit()
        _audit('ADMIN_DELETED_FACULTY', f'Deleted faculty {fid} ({name})')
        flash(f'Faculty {name} ({fid}) deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting faculty: {str(e)}', 'danger')

    return redirect(url_for('admin.faculty'))


@admin_bp.route('/faculty/<int:faculty_id>/enroll-face', methods=['GET', 'POST'])
@login_required
@role_required('ADMIN')
def enroll_faculty_face(faculty_id):
    """Enroll or re-enroll a faculty member's face."""
    f = Faculty.query.get_or_404(faculty_id)
    face_status = face_recognition_status()

    if request.method == 'POST':
        photo_file = request.files.get('photo')
        if not photo_file or not photo_file.filename:
            flash('Please upload a photo to enroll face.', 'danger')
            return render_template('admin/enroll_face.html', person=f, role='FACULTY', face_status=face_status)

        if not allowed_photo(photo_file.filename):
            flash('Invalid photo format. Use JPG, PNG, or WebP.', 'danger')
            return render_template('admin/enroll_face.html', person=f, role='FACULTY', face_status=face_status)

        file_bytes = photo_file.read()
        embedding, error = enroll_face_from_file(file_bytes)
        if error:
            flash(f'Face enrollment failed: {error}', 'danger')
            return render_template('admin/enroll_face.html', person=f, role='FACULTY', face_status=face_status)

        # Save photo
        ext = photo_file.filename.rsplit('.', 1)[1].lower()
        filename = secure_filename(f"{f.faculty_id}_enroll.{ext}")
        save_dir = os.path.join(_upload_dir(), 'faculty')
        os.makedirs(save_dir, exist_ok=True)
        with open(os.path.join(save_dir, filename), 'wb') as fp:
            fp.write(file_bytes)
        if not f.photo_path:
            f.photo_path = f'uploads/faculty/{filename}'

        FaceEmbedding.query.filter_by(user_id=f.user_id, is_active=True).update({'is_active': False})
        new_emb = FaceEmbedding(
            user_id=f.user_id,
            embedding_data=embedding,
            model_name=face_status.get('model', 'opencv_dnn_v1'),
            is_active=True
        )
        db.session.add(new_emb)
        db.session.commit()
        _audit('ADMIN_ENROLLED_FACULTY_FACE', f'Face enrolled for faculty {f.faculty_id}')
        flash(f'Face successfully enrolled for {f.user.name}!', 'success')
        return redirect(url_for('admin.faculty'))

    return render_template('admin/enroll_face.html', person=f, role='FACULTY', face_status=face_status)


# ═══════════════════════════════════════════════════════════════════════════════
# SUBJECTS
# ═══════════════════════════════════════════════════════════════════════════════
@admin_bp.route('/subjects')
@login_required
@role_required('ADMIN')
def subjects():
    all_subjects = Subject.query.all()
    return render_template('admin/subjects.html', subjects=all_subjects)

@admin_bp.route('/subjects/add', methods=['POST'])
@login_required
@role_required('ADMIN')
def add_subject():
    code = request.form.get('subject_code', '').strip().upper()
    name = request.form.get('subject_name', '').strip()
    short = request.form.get('short_name', '').strip().upper()
    credits = request.form.get('credits', 3, type=int)
    if not all([code, name, short]):
        flash('All fields are required.', 'danger')
        return redirect(url_for('admin.subjects'))
    if Subject.query.filter_by(subject_code=code).first():
        flash(f'Subject code {code} already exists.', 'danger')
        return redirect(url_for('admin.subjects'))
    sub = Subject(subject_code=code, subject_name=name, short_name=short, credits=credits)
    db.session.add(sub)
    db.session.commit()
    flash(f'Subject {short} added.', 'success')
    return redirect(url_for('admin.subjects'))

@admin_bp.route('/subjects/<int:sub_id>/toggle', methods=['POST'])
@login_required
@role_required('ADMIN')
def toggle_subject(sub_id):
    sub = Subject.query.get_or_404(sub_id)
    sub.is_active = not sub.is_active
    db.session.commit()
    status = 'activated' if sub.is_active else 'deactivated'
    flash(f'Subject {sub.short_name} {status}.', 'info')
    return redirect(url_for('admin.subjects'))


# ═══════════════════════════════════════════════════════════════════════════════
# FACE STATUS API
# ═══════════════════════════════════════════════════════════════════════════════
@admin_bp.route('/api/face-status')
@login_required
@role_required('ADMIN')
def api_face_status():
    return jsonify(face_recognition_status())


@admin_bp.route('/subjects/<int:sub_id>/delete', methods=['POST'])
@login_required
@role_required('ADMIN')
def delete_subject(sub_id):
    sub = Subject.query.get_or_404(sub_id)
    code_val = sub.subject_code
    short = sub.short_name
    try:
        Timetable.query.filter_by(subject_id=sub.id).delete()
        db.session.delete(sub)
        db.session.commit()
        _audit('ADMIN_DELETED_SUBJECT', f'Deleted subject {code_val} ({short})')
        flash(f'Subject {short} ({code_val}) deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting subject: {str(e)}', 'danger')

    return redirect(url_for('admin.subjects'))

@admin_bp.route('/timetable/<int:slot_id>/delete', methods=['POST'])
@login_required
@role_required('ADMIN')
def delete_timetable_slot_admin(slot_id):
    slot = Timetable.query.get_or_404(slot_id)
    try:
        db.session.delete(slot)
        db.session.commit()
        _audit('ADMIN_DELETED_TIMETABLE', f'Deleted timetable slot #{slot_id}')
        flash(f'Timetable slot #{slot_id} deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting timetable slot: {str(e)}', 'danger')

    return redirect(request.referrer or url_for('hod.timetable'))


# -----------------------------------------------------------------------------
# HOD MANAGEMENT
# -----------------------------------------------------------------------------
@admin_bp.route('/hod')
@login_required
@role_required('ADMIN')
def hod_list():
    hods = User.query.filter_by(role='HOD').all()
    return render_template('admin/hod.html', hods=hods)

@admin_bp.route('/hod/add', methods=['GET', 'POST'])
@login_required
@role_required('ADMIN')
def add_hod():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        department = request.form.get('department', 'CSE-AIML').strip()
        password = request.form.get('password', '').strip()

        if not all([name, username, email, department, password]):
            flash('All fields are required.', 'danger')
            return render_template('admin/add_hod.html')

        if User.query.filter_by(username=username).first():
            flash(f'Username "{username}" is already taken.', 'danger')
            return render_template('admin/add_hod.html')

        if User.query.filter_by(email=email).first():
            flash(f'Email "{email}" is already registered.', 'danger')
            return render_template('admin/add_hod.html')

        try:
            u = User(
                role='HOD',
                username=username,
                name=name,
                email=email,
                department=department,
                is_active=True,
                status='ACTIVE'
            )
            u.set_password(password)
            db.session.add(u)
            db.session.commit()
            _audit('ADMIN_ADDED_HOD', f'Admin added HOD {username} ({name})')
            flash(f'HOD {name} ({username}) created successfully!', 'success')
            return redirect(url_for('admin.hod_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding HOD: {str(e)}', 'danger')

    return render_template('admin/add_hod.html')

@admin_bp.route('/hod/<int:hod_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('ADMIN')
def edit_hod(hod_id):
    hod_user = User.query.filter_by(id=hod_id, role='HOD').first_or_404()
    if request.method == 'POST':
        hod_user.name = request.form.get('name', hod_user.name).strip()
        
        new_uname = request.form.get('username', '').strip()
        if new_uname and new_uname != hod_user.username:
            if User.query.filter_by(username=new_uname).first():
                flash(f'Username "{new_uname}" is already taken.', 'danger')
                return render_template('admin/edit_hod.html', hod=hod_user)
            hod_user.username = new_uname

        new_email = request.form.get('email', '').strip().lower()
        if new_email and new_email != hod_user.email:
            if User.query.filter_by(email=new_email).first():
                flash(f'Email "{new_email}" is already registered.', 'danger')
                return render_template('admin/edit_hod.html', hod=hod_user)
            hod_user.email = new_email

        new_dept = request.form.get('department', '').strip()
        if new_dept:
            hod_user.department = new_dept

        new_pass = request.form.get('password', '').strip()
        if new_pass:
            hod_user.set_password(new_pass)

        is_active = request.form.get('is_active') == 'on'
        hod_user.is_active = is_active
        hod_user.status = 'ACTIVE' if is_active else 'INACTIVE'

        try:
            db.session.commit()
            _audit('ADMIN_EDITED_HOD', f'Admin edited HOD {hod_user.username}')
            flash(f'HOD {hod_user.name} updated successfully.', 'success')
            return redirect(url_for('admin.hod_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Update failed: {str(e)}', 'danger')

    return render_template('admin/edit_hod.html', hod=hod_user)

@admin_bp.route('/hod/<int:hod_id>/toggle', methods=['POST'])
@login_required
@role_required('ADMIN')
def toggle_hod(hod_id):
    hod_user = User.query.filter_by(id=hod_id, role='HOD').first_or_404()
    hod_user.is_active = not hod_user.is_active
    hod_user.status = 'ACTIVE' if hod_user.is_active else 'INACTIVE'
    db.session.commit()
    status_str = "activated" if hod_user.is_active else "deactivated"
    _audit('ADMIN_TOGGLED_HOD', f'{status_str.capitalize()} HOD {hod_user.username}')
    flash(f'HOD {hod_user.name} {status_str}.', 'info')
    return redirect(url_for('admin.hod_list'))

@admin_bp.route('/hod/<int:hod_id>/delete', methods=['POST'])
@login_required
@role_required('ADMIN')
def delete_hod(hod_id):
    hod_user = User.query.filter_by(id=hod_id, role='HOD').first_or_404()
    uname = hod_user.username
    name = hod_user.name
    try:
        FaceEmbedding.query.filter_by(user_id=hod_user.id).delete()
        db.session.delete(hod_user)
        db.session.commit()
        _audit('ADMIN_DELETED_HOD', f'Deleted HOD {uname} ({name})')
        flash(f'HOD {name} ({uname}) deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting HOD: {str(e)}', 'danger')
    return redirect(url_for('admin.hod_list'))


# -----------------------------------------------------------------------------
# GLOBAL USER DIRECTORY & MANAGEMENT
# -----------------------------------------------------------------------------
@admin_bp.route('/users')
@login_required
@role_required('ADMIN')
def users_list():
    search = request.args.get('search', '').strip()
    role_filter = request.args.get('role', '').strip().upper()
    status_filter = request.args.get('status', '').strip().upper()

    query = User.query
    if search:
        query = query.filter(
            (User.name.ilike(f'%{search}%')) |
            (User.username.ilike(f'%{search}%')) |
            (User.email.ilike(f'%{search}%'))
        )
    if role_filter and role_filter in ['STUDENT', 'FACULTY', 'HOD', 'ADMIN']:
        query = query.filter_by(role=role_filter)
    if status_filter in ['ACTIVE', 'INACTIVE']:
        is_act = (status_filter == 'ACTIVE')
        query = query.filter_by(is_active=is_act)

    all_users = query.order_by(User.id.asc()).all()
    return render_template('admin/users.html',
                           users=all_users,
                           search=search,
                           role_filter=role_filter,
                           status_filter=status_filter)

@admin_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
@role_required('ADMIN')
def reset_user_password(user_id):
    target_user = User.query.get_or_404(user_id)
    new_password = request.form.get('new_password', '').strip()
    if not new_password or len(new_password) < 4:
        flash('Password must be at least 4 characters long.', 'danger')
        return redirect(request.referrer or url_for('admin.users_list'))

    target_user.set_password(new_password)
    db.session.commit()
    _audit('ADMIN_RESET_PASSWORD', f'Reset password for user {target_user.username} ({target_user.role})')
    flash(f'Password for {target_user.username} ({target_user.name}) has been reset successfully.', 'success')
    return redirect(request.referrer or url_for('admin.users_list'))

@admin_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@role_required('ADMIN')
def toggle_user(user_id):
    if user_id == session.get('user_id'):
        flash('You cannot deactivate your own active admin session.', 'warning')
        return redirect(request.referrer or url_for('admin.users_list'))

    target_user = User.query.get_or_404(user_id)
    target_user.is_active = not target_user.is_active
    target_user.status = 'ACTIVE' if target_user.is_active else 'INACTIVE'
    db.session.commit()
    status_str = "activated" if target_user.is_active else "deactivated"
    _audit('ADMIN_TOGGLED_USER', f'{status_str.capitalize()} user {target_user.username}')
    flash(f'User {target_user.username} has been {status_str}.', 'info')
    return redirect(request.referrer or url_for('admin.users_list'))

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@role_required('ADMIN')
def delete_user(user_id):
    if user_id == session.get('user_id'):
        flash('You cannot delete your own admin account.', 'danger')
        return redirect(request.referrer or url_for('admin.users_list'))

    target_user = User.query.get_or_404(user_id)
    role = target_user.role
    uname = target_user.username
    name = target_user.name

    try:
        if role == 'STUDENT' and target_user.student_profile:
            st = target_user.student_profile
            AttendanceRecord.query.filter_by(student_id=st.id).delete()
            db.session.delete(st)
        elif role == 'FACULTY' and target_user.faculty_profile:
            f = target_user.faculty_profile
            Timetable.query.filter_by(faculty_id=f.id).delete()
            FacultyAttendance.query.filter_by(faculty_id=f.id).delete()
            AttendanceSession.query.filter_by(faculty_id=f.id).delete()
            db.session.delete(f)

        FaceEmbedding.query.filter_by(user_id=target_user.id).delete()
        db.session.delete(target_user)
        db.session.commit()
        _audit('ADMIN_DELETED_USER', f'Deleted user {uname} ({role} - {name})')
        flash(f'User {name} ({uname}) deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'danger')

    return redirect(request.referrer or url_for('admin.users_list'))
