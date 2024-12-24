from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response, session, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from auth import AuthService
from student_service import StudentService
from teacher_service import TeacherService
from admin_service import AdminService
from counselor_service import CounselorService
import io
import csv
from datetime import datetime
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import random
import string

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'  # 用于session加密

# 登录管理
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

auth_service = AuthService()
student_service = StudentService()
teacher_service = TeacherService()
admin_service = AdminService()
counselor_service = CounselorService()


class User(UserMixin):
    def __init__(self, user_data):
        self.id = user_data['user_id']
        self.role = user_data['role']


@login_manager.user_loader
def load_user(user_id):
    try:
        query = """
        SELECT 
            u.user_id,
            u.role,
            COALESCE(s.student_id, t.teacher_id) as role_id
        FROM Users u
        LEFT JOIN Students s ON u.user_id = s.user_id
        LEFT JOIN Teachers t ON u.user_id = t.user_id
        WHERE u.user_id = %s
        """
        result = auth_service.db.fetch_one(query, (user_id,))
        if result:
            user_data = {
                'user_id': result[2] or result[0],
                'role': result[1]
            }
            return User(user_data)
        return None
    except Exception as e:
        print(f"Error loading user: {e}")
        return None


@app.route('/')
def index():
    return redirect(url_for('login'))


def generate_captcha():
    # 生成随机验证码
    chars = string.ascii_letters + string.digits
    code = ''.join(random.choices(chars, k=4))

    # 创建图片
    width = 120
    height = 40
    image = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(image)

    # 添加干扰线
    for i in range(5):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line([(x1, y1), (x2, y2)], fill='gray')

    # 添加验证码文字
    font_size = 30
    try:
        font = ImageFont.truetype('arial.ttf', font_size)
    except:
        font = ImageFont.load_default()

    for i, char in enumerate(code):
        x = 15 + i * 25
        y = random.randint(5, 15)
        draw.text((x, y), char, font=font, fill='black')

    # 保存验证码到session
    session['captcha'] = code.lower()

    # 返回图片
    img_io = BytesIO()
    image.save(img_io, 'PNG')
    img_io.seek(0)
    return img_io


# 添加验证码路由
@app.route('/captcha')
def get_captcha():
    img_io = generate_captcha()
    return send_file(img_io, mimetype='image/png')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        captcha = request.form.get('captcha', '').lower()

        # 验证验证码
        if captcha != session.get('captcha', ''):
            flash('验证码错误', 'danger')
            return render_template('login.html')

        user_data = auth_service.login(username, password)

        if user_data:
            user = User(user_data)
            login_user(user)

            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'teacher':
                return redirect(url_for('teacher_dashboard'))
            elif user.role == 'student':
                return redirect(url_for('student_dashboard'))
            elif user.role == 'counselor':
                return redirect(url_for('counselor_dashboard'))

        flash('用户名或密码错误', 'danger')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# 管理员相关路由
@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    return render_template('admin/dashboard.html')


@app.route('/api/admin/classes/list', methods=['GET'])
@login_required
def get_classes_list():
    if current_user.role != 'admin':
        return jsonify({'error': '无权访问'}), 403
    try:
        classes = admin_service.get_classes_list()
        print(f"Debug - Classes data from service: {classes}")
        return jsonify(classes)
    except Exception as e:
        print(f"Error in get_classes_list: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/teachers/list', methods=['GET'])
@login_required
def get_teachers_list():
    if current_user.role != 'admin':
        return jsonify({'error': '无权访问'}), 403
    try:
        teachers = admin_service.get_teachers_list()
        print(f"Debug - Teachers data: {teachers}")
        return jsonify(teachers)
    except Exception as e:
        print(f"Error in get_teachers_list: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/courses/list', methods=['GET'])
@login_required
def get_courses_list():
    if current_user.role != 'admin':
        return jsonify({'error': '无权访问'}), 403
    try:
        courses = admin_service.get_courses_list()
        print(f"Debug - Courses data: {courses}")
        return jsonify(courses)
    except Exception as e:
        print(f"Error in get_courses_list: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/students/list', methods=['GET'])
@login_required
def get_students_list():
    if current_user.role != 'admin':
        return jsonify({'error': '无权访问'}), 403
    try:
        students = admin_service.get_students_list()
        print(f"Debug - Students data: {students}")
        return jsonify(students)
    except Exception as e:
        print(f"Error in get_students_list: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/reports/teacher-workload', methods=['GET'])
@login_required
def get_teacher_workload_report():
    if current_user.role != 'admin':
        return jsonify({'error': '无权访问'}), 403
    try:
        data = admin_service.get_teacher_workload_report()
        return jsonify(data)
    except Exception as e:
        print(f"Error in get_teacher_workload_report: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/reports/course-selection', methods=['GET'])
@login_required
def get_course_selection_report():
    if current_user.role != 'admin':
        return jsonify({'error': '无权访问'}), 403
    try:
        data = admin_service.get_course_selection_report()
        return jsonify(data)
    except Exception as e:
        print(f"Error in get_course_selection_report: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/classes/add', methods=['POST'])
@login_required
def add_class_api():
    if current_user.role != 'admin':
        return jsonify({'error': '无权访问'}), 403
    try:
        name = request.form.get('name')
        major_id = request.form.get('majorId')
        counselor_id = request.form.get('counselorId')

        if not all([name, major_id]):
            return jsonify({'error': '班级名称和专业是必填项'}), 400

        result = admin_service.add_class(name, major_id, counselor_id)
        if result:
            return jsonify({'success': True})

        return jsonify({'error': '添加班级失败'}), 400

    except Exception as e:
        print(f"Error in add_class_api: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/counselors/list', methods=['GET'])
@login_required
def get_counselors_list():
    if current_user.role != 'admin':
        return jsonify({'error': '无权访问'}), 403
    try:
        counselors = admin_service.get_counselors_list()
        return jsonify(counselors)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/majors/options', methods=['GET'])
@login_required
def get_majors_options():
    if current_user.role != 'admin':
        return jsonify({'error': '无权访问'}), 403
    try:
        query = """
        SELECT major_id, name 
        FROM Majors 
        ORDER BY name
        """
        majors = admin_service.db.fetch_all(query)
        return jsonify([{
            'id': m[0],
            'name': m[1]
        } for m in majors])
    except Exception as e:
        print(f"Error in get_majors_options: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/classes/options', methods=['GET'])
@login_required
def get_classes_options():
    if current_user.role != 'admin':
        return jsonify({'error': '无权访问'}), 403
    try:
        query = """
        SELECT c.class_id, c.name, m.name as major_name
        FROM Classes c
        JOIN Majors m ON c.major_id = m.major_id
        ORDER BY c.name
        """
        classes = admin_service.db.fetch_all(query)
        return jsonify([{
            'id': c[0],
            'name': f"{c[1]} ({c[2]})"  # 显示格式：班级名称 (专业名称)
        } for c in classes])
    except Exception as e:
        print(f"Error in get_classes_options: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/majors/list', methods=['GET'])
@login_required
def get_majors_list():
    if current_user.role != 'admin':
        return jsonify({'error': '无权访问'}), 403
    try:
        majors = admin_service.get_majors_list()
        print(f"Debug - Majors data: {majors}")
        return jsonify(majors)
    except Exception as e:
        print(f"Error in get_majors_list: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/semesters/list', methods=['GET'])
@login_required
def get_semesters_list():
    if current_user.role != 'admin':
        return jsonify({'error': '无权访问'}), 403
    try:
        semesters = admin_service.get_semesters_list()
        return jsonify(semesters)
    except Exception as e:
        print(f"Error in get_semesters_list: {e}")
        return jsonify({'error': str(e)}), 500


# 教师管理相关路由
@app.route('/api/admin/teachers/<teacher_id>', methods=['GET'])
@login_required
def get_teacher(teacher_id):
    if current_user.role != 'admin':
        return jsonify({'error': '无权访问'}), 403
    try:
        teacher = admin_service.get_teacher_by_id(teacher_id)
        if teacher:
            return jsonify({
                'teacher_id': teacher[0],
                'name': teacher[1],
                'title': teacher[2],
                'department': teacher[3]
            })
        return jsonify({'error': '教师不存在'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/teachers/<teacher_id>', methods=['DELETE'])
@login_required
def delete_teacher(teacher_id):
    if current_user.role != 'admin':
        return jsonify({'error': '无权访问'}), 403
    try:
        admin_service.delete_teacher(teacher_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/teachers/add', methods=['POST'])
@login_required
def add_teacher():
    if current_user.role != 'admin':
        return jsonify({'error': '无权访问'}), 403
    try:
        name = request.form.get('name')
        title = request.form.get('title')
        department = request.form.get('department')

        print(f"Debug - Received teacher data: name={name}, title={title}, department={department}")

        if not all([name, title, department]):
            print(f"Debug - Missing required fields")
            return jsonify({'error': '教师姓名、职称和院系是必填项'}), 400

        result = admin_service.add_teacher(name, title, department)
        if result:
            print(f"Debug - Teacher added successfully")
            return jsonify({'success': True})

        print(f"Debug - Failed to add teacher")
        return jsonify({'error': '添加教师失败'}), 400

    except Exception as e:
        print(f"Error in add_teacher: {e}")
        return jsonify({'error': str(e)}), 500


# 课程管理相关路由
@app.route('/api/admin/courses/<course_id>', methods=['GET'])
@login_required
def get_course(course_id):
    if current_user.role != 'admin':
        return jsonify({'error': '无权访问'}), 403
    try:
        course = admin_service.get_course_by_id(course_id)
        if course:
            return jsonify(course)
        return jsonify({'error': '课程不存在'}), 404
    except Exception as e:
        print(f"Error in get_course: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/courses/<course_id>', methods=['DELETE'])
@login_required
def delete_course(course_id):
    if current_user.role != 'admin':
        return jsonify({'error': '无权访问'}), 403
    try:
        admin_service.delete_course(course_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/courses/<course_id>', methods=['PUT'])
@login_required
def update_course(course_id):
    if current_user.role != 'admin':
        return jsonify({'error': '无权访问'}), 403
    try:
        data = request.get_json()
        print(f"Debug - Update course request data: {data}")

        result = admin_service.update_course(course_id, data)

        if result:
            return jsonify({'success': True})
        else:
            return jsonify({'error': '更新失败'}), 500
    except Exception as e:
        print(f"Error in update_course route: {e}")
        return jsonify({'error': str(e)}), 500


# 班级管理相关路由
@app.route('/api/admin/classes/<class_id>', methods=['GET'])
@login_required
def get_class(class_id):
    if current_user.role != 'admin':
        return jsonify({'error': '无权访问'}), 403
    try:
        class_info = admin_service.get_class_by_id(class_id)
        if class_info:
            return jsonify({
                'class_id': class_info[0],
                'name': class_info[1],
                'major_id': class_info[2],
                'counselor_id': class_info[3]
            })
        return jsonify({'error': '班级不存在'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/classes/<class_id>/students', methods=['GET'])
@login_required
def get_class_students(class_id):
    if current_user.role != 'admin':
        return jsonify({'error': '无权访问'}), 403
    try:
        students = admin_service.get_class_students(class_id)
        return jsonify(students)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/classes/<class_id>', methods=['DELETE'])
@login_required
def delete_class(class_id):
    if current_user.role != 'admin':
        return jsonify({'error': '无权访问'}), 403
    try:
        admin_service.delete_class(class_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/classes/<class_id>', methods=['PUT'])
@login_required
def update_class(class_id):
    if current_user.role != 'admin':
        return jsonify({'error': '无权访问'}), 403
    try:
        data = request.get_json()
        print(f"Debug - Update class request data: {data}")

        result = admin_service.update_class(
            class_id,
            name=data.get('name'),
            major_id=data.get('major_id'),
            counselor_id=data.get('counselor_id')
        )

        if result:
            return jsonify({'success': True})
        else:
            return jsonify({'error': '更新失败'}), 500
    except Exception as e:
        print(f"Error in update_class route: {e}")
        return jsonify({'error': str(e)}), 500


# 专业管理相关路由
@app.route('/api/admin/majors/<major_id>', methods=['GET'])
@login_required
def get_major(major_id):
    if current_user.role != 'admin':
        return jsonify({'error': '无权访问'}), 403
    try:
        major = admin_service.get_major_by_id(major_id)
        if major:
            return jsonify({
                'major_id': major[0],
                'name': major[1],
                'department': major[2]
            })
        return jsonify({'error': '专业不存在'}), 404
    except Exception as e:
        print(f"Error in get_major: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/majors/add', methods=['POST'])
@login_required
def add_major():
    if current_user.role != 'admin':
        return jsonify({'error': '无权访问'}), 403
    try:
        name = request.form.get('name')
        department = request.form.get('department')

        if not all([name, department]):
            return jsonify({'error': '专业名称和院系是必填项'}), 400

        result = admin_service.add_major(name, department)
        if result:
            return jsonify({'success': True})

        return jsonify({'error': '添加专业失败'}), 400

    except Exception as e:
        print(f"Error in add_major: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/majors/<major_id>', methods=['PUT'])
@login_required
def update_major(major_id):
    if current_user.role != 'admin':
        return jsonify({'error': '无权访问'}), 403
    try:
        data = request.get_json()
        print(f"Debug - Update major request data: {data}")

        result = admin_service.update_major(
            major_id,
            name=data.get('name'),
            department=data.get('department')
        )

        if result:
            return jsonify({'success': True})
        else:
            return jsonify({'error': '更新失败'}), 500
    except Exception as e:
        print(f"Error in update_major route: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/majors/<major_id>', methods=['DELETE'])
@login_required
def delete_major(major_id):
    if current_user.role != 'admin':
        return jsonify({'error': '无权访问'}), 403
    try:
        admin_service.delete_major(major_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/courses/add', methods=['POST'])
@login_required
def add_course():
    if current_user.role != 'admin':
        return jsonify({'error': '无权访问'}), 403
    try:
        data = {
            'name': request.form.get('name'),
            'credits': request.form.get('credits'),
            'hours': request.form.get('hours'),
            'teacher_id': request.form.get('teacher_id') or None,
            'semester_id': request.form.get('semester_id') or None,
            'max_students': request.form.get('max_students')
        }

        # 生成课程ID
        course_id = admin_service.generate_course_id()
        data['course_id'] = course_id

        print(f"Debug - Add course data: {data}")

        result = admin_service.add_course(data)
        if result:
            return jsonify({'success': True})
        return jsonify({'error': '添加课程失败'}), 400

    except Exception as e:
        print(f"Error in add_course: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/semesters/<int:semester_id>', methods=['GET'])
@login_required
def get_semester(semester_id):
    if current_user.role != 'admin':
        return jsonify({'error': '无权访问'}), 403
    try:
        semester = admin_service.get_semester_by_id(semester_id)
        if semester:
            return jsonify({
                'semester_id': semester[0],
                'name': semester[1],
                'start_date': semester[2].strftime('%Y-%m-%d'),
                'end_date': semester[3].strftime('%Y-%m-%d'),
                'status': semester[4]
            })
        return jsonify({'error': '学期不存在'}), 404
    except Exception as e:
        print(f"Error in get_semester: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/semesters/add', methods=['POST'])
@login_required
def add_semester():
    if current_user.role != 'admin':
        return jsonify({'error': '无权访问'}), 403
    try:
        data = {
            'name': request.form.get('name'),
            'start_date': request.form.get('start_date'),
            'end_date': request.form.get('end_date'),
            'status': int(request.form.get('status', 0))
        }

        print(f"Debug - Add semester data: {data}")

        result = admin_service.add_semester(**data)
        if result:
            return jsonify({'success': True})
        return jsonify({'error': '添加学期失败'}), 400

    except Exception as e:
        print(f"Error in add_semester: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/semesters/<int:semester_id>', methods=['PUT'])
@login_required
def update_semester(semester_id):
    if current_user.role != 'admin':
        return jsonify({'error': '无权访问'}), 403
    try:
        data = request.get_json()
        print(f"Debug - Update semester request data: {data}")

        result = admin_service.update_semester(
            semester_id,
            name=data.get('name'),
            start_date=data.get('start_date'),
            end_date=data.get('end_date'),
            status=data.get('status')
        )

        if result:
            return jsonify({'success': True})
        else:
            return jsonify({'error': '更新失败'}), 500
    except Exception as e:
        print(f"Error in update_semester route: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/semesters/<int:semester_id>', methods=['DELETE'])
@login_required
def delete_semester(semester_id):
    if current_user.role != 'admin':
        return jsonify({'error': '无权访问'}), 403
    try:
        admin_service.delete_semester(semester_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/reports/export/<report_type>')
@login_required
def export_report(report_type):
    if current_user.role != 'admin':
        return jsonify({'error': '无权访问'}), 403

    try:
        columns, results = admin_service.export_report(report_type)
        if not results:
            return jsonify({'error': '导出失败'}), 500

        # 创建CSV响应
        output = io.StringIO()
        writer = csv.writer(output)

        # 写入表头
        writer.writerow(columns)

        # 写入数据
        for row in results:
            writer.writerow(row)

        # 设置响应头
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename={report_type}_{datetime.now().strftime("%Y%m%d")}.csv'
            }
        )

    except Exception as e:
        print(f"Error in export_report: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/counselor')
@login_required
def counselor_dashboard():
    if current_user.role != 'counselor':
        return redirect(url_for('login'))
    try:
        classes = counselor_service.get_managed_classes(current_user.id)
        print(f"Debug - Classes for counselor dashboard: {classes}")
        return render_template('counselor/dashboard.html', classes=classes)
    except Exception as e:
        print(f"Error in counselor_dashboard: {e}")
        flash('获取数据失败', 'danger')
        return redirect(url_for('login'))


@app.route('/counselor/class/<class_id>')
@login_required
def view_class_students(class_id):
    if current_user.role != 'counselor':
        return redirect(url_for('login'))
    try:
        students = counselor_service.get_class_students(class_id)
        stats = counselor_service.get_class_stats(class_id)
        distribution = counselor_service.get_class_grade_distribution(class_id)
        class_info = counselor_service.get_class_info(class_id)

        print(f"Debug - Class info: {class_info}")
        print(f"Debug - Class stats: {stats}")
        print(f"Debug - Grade distribution: {distribution}")

        return render_template('counselor/class_analysis.html',
                               class_info=class_info,
                               students=students,
                               stats=stats,
                               distribution=distribution,
                               class_id=class_id)
    except Exception as e:
        print(f"Error in view_class_students: {e}")
        flash('获取数据失败', 'danger')
        return redirect(url_for('counselor_dashboard'))


@app.route('/api/counselor/student/<student_id>/courses')
@login_required
def get_student_courses(student_id):
    if current_user.role != 'counselor':
        return jsonify({'error': '无权访问'}), 403
    courses = counselor_service.get_student_courses(student_id)
    return jsonify({'data': courses})


@app.route('/api/counselor/student/<student_id>/toggle-risk', methods=['POST'])
@login_required
def toggle_student_risk(student_id):
    if current_user.role != 'counselor':
        return jsonify({'error': '无权访问'}), 403

    try:
        success = counselor_service.toggle_student_risk_status(student_id, current_user.id)
        if success:
            return jsonify({'success': True})
        return jsonify({'error': '操作失败'}), 500
    except Exception as e:
        print(f"Error in toggle_student_risk: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/counselor/class/<class_id>/export')
@login_required
def export_class_report(class_id):
    if current_user.role != 'counselor':
        return jsonify({'error': '无权访问'}), 403

    try:
        data = counselor_service.export_class_report(class_id)
        if not data:
            return jsonify({'error': '导出失败'}), 500

        output = io.StringIO()
        writer = csv.writer(output)

        # 写入表头
        writer.writerow(['学号', '姓名', '选课数', '平均分', '不及格课程数', '重点关注'])

        # 写入数据
        writer.writerows(data)

        # 设置响应头
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=class_report_{class_id}_{datetime.now().strftime("%Y%m%d")}.csv'
            }
        )
    except Exception as e:
        print(f"Error in export_class_report: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/student')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        return jsonify({'error': '无权访问'}), 403

    # 获取学生的成绩信息
    grades = student_service.get_student_grades(current_user.id)
    return render_template('student/dashboard.html', grades=grades)


@app.route('/teacher')
@login_required
def teacher_dashboard():
    if current_user.role != 'teacher':
        return redirect(url_for('login'))
    return render_template('teacher/dashboard.html')


# 学生相关路由
@app.route('/api/student/courses/available')
@login_required
def get_available_courses():
    if current_user.role != 'student':
        return jsonify({'error': '无权访问'}), 403
    courses = student_service.query_available_courses(current_user.id)
    return jsonify(courses)


@app.route('/api/student/courses/selected')
@login_required
def get_selected_courses():
    if current_user.role != 'student':
        return jsonify({'error': '无权访问'}), 403
    courses = student_service.get_selected_courses(current_user.id)
    return jsonify(courses)


@app.route('/api/student/courses/select', methods=['POST'])
@login_required
def select_course():
    if current_user.role != 'student':
        return jsonify({'error': '无权访问'}), 403

    course_id = request.form.get('course_id')
    if not course_id:
        return jsonify({'error': '参数错误'}), 400

    success = student_service.select_course(current_user.id, course_id)
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'error': '选课失败'}), 500


@app.route('/api/student/course/drop', methods=['POST'])
@login_required
def drop_course():
    if current_user.role != 'student':
        return jsonify({'error': '无权访问'}), 403

    course_id = request.form.get('course_id')
    if not course_id:
        return jsonify({'error': '参数错误'}), 400

    success = student_service.drop_course(current_user.id, course_id)
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'error': '退课失败'}), 500


@app.route('/teacher/courses/<course_id>/students')
@login_required
def view_course_students(course_id):
    if current_user.role != 'teacher':
        return redirect(url_for('login'))

    course = teacher_service.get_course_info(course_id)
    if not course:
        flash('课程不存在', 'danger')
        return redirect(url_for('teacher_dashboard'))

    return render_template('teacher/course_management.html', course=course)


@app.route('/teacher/courses/<course_id>/analysis')
@login_required
def course_grade_analysis(course_id):
    if current_user.role != 'teacher':
        return redirect(url_for('login'))

    # 获取课程信息
    course = teacher_service.get_course_info(course_id)
    if not course:
        flash('课程不存在', 'danger')
        return redirect(url_for('teacher_dashboard'))

    # 获取成绩分析数据
    stats = teacher_service.get_course_stats(course_id)
    return render_template('teacher/grade_analysis.html', course=course, stats=stats)


# 教师相关路由
@app.route('/api/teacher/courses')
@login_required
def get_teacher_courses():
    if current_user.role != 'teacher':
        return jsonify({'error': '无权访问'}), 403
    return jsonify(teacher_service.get_teaching_courses(current_user.id))


@app.route('/api/teacher/courses/<course_id>/students')
@login_required
def get_course_students(course_id):
    if current_user.role != 'teacher':
        return jsonify({'error': '无权访问'}), 403
    try:
        students = teacher_service.get_course_students_detail(course_id)
        return jsonify({'data': students})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/teacher/input-grade', methods=['POST'])
@login_required
def input_grade():
    if current_user.role != 'teacher':
        return jsonify({'error': '无权访问'}), 403

    try:
        course_id = request.form.get('course_id')
        student_id = request.form.get('student_id')
        score = float(request.form.get('score'))
        grade_type = request.form.get('grade_type')

        teacher_service.input_grade(course_id, student_id, score, grade_type)
        return jsonify({'success': True})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/grades/analyze')
@login_required
def analyze_grades():
    if current_user.role != 'teacher':
        return jsonify({'error': '无权访问'}), 403

    course_id = request.args.get('course_id')
    stats = teacher_service.get_course_stats(course_id)
    if stats:
        return jsonify(stats)
    return jsonify({'error': '无数据'}), 404


@app.route('/api/teacher/courses/<course_id>/grades')
@login_required
def get_course_grades(course_id):
    if current_user.role != 'teacher':
        return jsonify({'error': '无权访问'}), 403
    grades = teacher_service.get_course_grades_detail(course_id)
    return jsonify({'data': grades})


@app.route('/teacher/courses/<course_id>/export')
@login_required
def export_course_students(course_id):
    if current_user.role != 'teacher':
        return jsonify({'error': '无权访问'}), 403

    try:
        data = teacher_service.get_course_students_export(course_id)
        if not data:
            return jsonify({'error': '导出失败'}), 500

        output = io.StringIO()
        writer = csv.writer(output)

        # 写入表头
        writer.writerow(['学号', '姓名', '班级', '专业', '成绩', '考试类型', '录入时间'])

        # 写入数据
        writer.writerows(data)

        # 设置响应头
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=course_students_{course_id}_{datetime.now().strftime("%Y%m%d")}.csv'
            }
        )
    except Exception as e:
        print(f"Error in export_course_students: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/teacher/courses/<course_id>/export-grades')
@login_required
def export_course_grades(course_id):
    if current_user.role != 'teacher':
        return jsonify({'error': '无权访问'}), 403

    try:
        data = teacher_service.export_course_grades(course_id)
        if not data:
            return jsonify({'error': '导出失败'}), 500

        output = io.StringIO()
        writer = csv.writer(output)

        # 写入表头
        writer.writerow(['学号', '姓名', '课程名称', '成绩', '考试类型', '录入时间'])

        # 写入数据
        writer.writerows(data)

        # 设置响应头
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=course_grades_{course_id}_{datetime.now().strftime("%Y%m%d")}.csv'
            }
        )
    except Exception as e:
        print(f"Error in export_course_grades: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)