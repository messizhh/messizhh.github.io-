from db_connection import DatabaseConnection
from datetime import datetime


class AdminService:
    def __init__(self):
        self.db = DatabaseConnection()

    def add_major(self, name, department):
        query = """
        INSERT INTO Majors (name, department) 
        VALUES (%s, %s)
        """
        return bool(self.db.execute_query(query, (name, department)))

    def update_major(self, major_id, name=None, department=None):
        updates = []
        params = []
        if name:
            updates.append("name = %s")
            params.append(name)
        if department:
            updates.append("department = %s")
            params.append(department)

        if not updates:
            return True

        query = f"UPDATE Majors SET {', '.join(updates)} WHERE major_id = %s"
        params.append(major_id)
        return bool(self.db.execute_query(query, tuple(params)))

    def delete_major(self, major_id):
        query = "DELETE FROM Majors WHERE major_id = %s"
        return bool(self.db.execute_query(query, (major_id,)))

    def generate_workload_report(self):
        query = """
        SELECT * FROM Teacher_Workload
        """
        return self.db.fetch_all(query)

    def manage_semester(self, name, start_date, end_date, status=1):
        query = """
        INSERT INTO Semesters (name, start_date, end_date, status)
        VALUES (%s, %s, %s, %s)
        """
        return bool(self.db.execute_query(query, (name, start_date, end_date, status)))

    def log_action(self, user_id, action_type, target_type, target_id, details):
        query = """
        INSERT INTO System_Logs 
        (user_id, action_type, target_type, target_id, details)
        VALUES (%s, %s, %s, %s, %s)
        """
        return bool(self.db.execute_query(query,
                                          (user_id, action_type, target_type, target_id, details)))

    def get_all_majors(self):
        query = "SELECT major_id, name, department FROM Majors"
        return self.db.fetch_all(query)

    def add_class(self, name, major_id, counselor_id=None):
        """添加班级"""
        try:
            query = """
            INSERT INTO Classes (name, major_id, counselor_id)
            VALUES (%s, %s, %s)
            """
            print(f"Debug - Adding class: name={name}, major_id={major_id}, counselor_id={counselor_id}")
            result = self.db.execute_query(query, (name, major_id, counselor_id))
            return bool(result)
        except Exception as e:
            print(f"Error in add_class: {e}")
            return False

    def update_class(self, class_id, name=None, major_id=None, counselor_id=None):
        """更新班级信息"""
        try:
            updates = []
            params = []
            if name:
                updates.append("name = %s")
                params.append(name)
            if major_id:
                updates.append("major_id = %s")
                params.append(major_id)
            if counselor_id is not None:  # 允许设置为 NULL
                updates.append("counselor_id = %s")
                params.append(counselor_id if counselor_id != '' else None)

            if not updates:
                return True

            query = f"UPDATE Classes SET {', '.join(updates)} WHERE class_id = %s"
            params.append(class_id)

            # 添加调试信息
            print(f"Debug - Update class query: {query}")
            print(f"Debug - Update class params: {params}")

            result = self.db.execute_query(query, tuple(params))

            # 验证更新结果
            if result:
                updated_class = self.get_class_by_id(class_id)
                print(f"Debug - Updated class data: {updated_class}")

            return bool(result)
        except Exception as e:
            print(f"Error in update_class: {e}")
            return False

    def delete_class(self, class_id):
        query = "DELETE FROM Classes WHERE class_id = %s"
        return bool(self.db.execute_query(query, (class_id,)))

    def add_user(self, username, password, role, email=None, phone=None):
        query = """
        INSERT INTO Users (user_id, username, password, role, email, phone)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        user_id = self.generate_user_id(role)
        return bool(self.db.execute_query(query, (user_id, username, password, role, email, phone)))

    def generate_user_id(self, role):
        """生成用户ID"""
        query = "SELECT MAX(user_id) FROM Users WHERE role = %s"
        result = self.db.fetch_one(query, (role,))

        if result and result[0]:
            last_id = int(result[0][1:])  # 去掉前缀后的数字
            new_id = last_id + 1
        else:
            new_id = 1

        prefix = {'student': 'S', 'teacher': 'T', 'admin': 'A', 'counselor': 'C'}
        return f"{prefix[role]}{new_id:06d}"

    def add_course(self, course_data):
        query = """
        INSERT INTO Courses (course_id, name, credits, hours, semester_id, 
                            teacher_id, max_students, description)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        return bool(self.db.execute_query(query, (
            course_data['course_id'],
            course_data['name'],
            course_data['credits'],
            course_data['hours'],
            course_data['semester_id'],
            course_data['teacher_id'],
            course_data['max_students'],
            course_data.get('description')
        )))

    def update_course(self, course_id, course_data):
        """更新课程信息"""
        try:
            # 首先检查课程是否存在
            check_query = "SELECT 1 FROM Courses WHERE course_id = %s"
            exists = self.db.fetch_one(check_query, (course_id,))
            if not exists:
                print(f"Debug - Course {course_id} not found")
                return False

            updates = []
            params = []

            # 定义字段和它们的数据类型转换函数
            fields = {
                'name': ('name', str),
                'credits': ('credits', int),
                'hours': ('hours', int),
                'teacher_id': ('teacher_id', str),
                'semester_id': ('semester_id', int),
                'max_students': ('max_students', int)
            }

            for key, (field, type_func) in fields.items():
                if key in course_data:
                    value = course_data[key]
                    if value == '':  # 处理空字符串
                        if field in ['teacher_id']:
                            value = None
                        else:
                            continue  # 跳过其他字段的空值
                    else:
                        try:
                            # 尝试转换数据类型
                            value = type_func(value)
                        except (ValueError, TypeError):
                            print(f"Warning: Failed to convert {key}={value} to {type_func}")
                            continue

                    updates.append(f"{field} = %s")
                    params.append(value)

            if not updates:
                print("Debug - No fields to update")
                return True

            query = f"UPDATE Courses SET {', '.join(updates)} WHERE course_id = %s"
            params.append(course_id)

            print(f"Debug - Update course query: {query}")
            print(f"Debug - Update course params: {params}")

            # 开始事务
            self.db.start_transaction()
            try:
                result = self.db.execute_query(query, tuple(params))
                print(f"Debug - Update result: {result}")

                # 提交事务
                self.db.commit()
                print("Debug - Transaction committed successfully")
                return True

            except Exception as e:
                # 回滚事务
                self.db.rollback()
                print(f"Debug - Transaction rolled back due to error: {e}")
                raise

        except Exception as e:
            print(f"Error in update_course: {e}")
            return False

    def delete_course(self, course_id):
        query = "DELETE FROM Courses WHERE course_id = %s"
        return bool(self.db.execute_query(query, (course_id,)))

    def generate_course_report(self):
        """生成课程报表"""
        query = """
        SELECT 
            c.course_id,
            c.name as course_name,
            t.name as teacher_name,
            c.credits,
            COUNT(cs.selection_id) as student_count,
            c.max_students,
            s.name as semester
        FROM Courses c
        JOIN Teachers t ON c.teacher_id = t.teacher_id
        JOIN Semesters s ON c.semester_id = s.semester_id
        LEFT JOIN Course_Selections cs ON c.course_id = cs.course_id
        GROUP BY c.course_id
        """
        return self.db.fetch_all(query)

    def get_user_list(self, role=None):
        """获取用户列表"""
        if role:
            query = """
            SELECT user_id, username, email, phone, status, created_at
            FROM Users WHERE role = %s
            """
            return self.db.fetch_all(query, (role,))
        else:
            query = """
            SELECT user_id, username, role, email, phone, status, created_at
            FROM Users
            """
            return self.db.fetch_all(query)

    def get_teacher_workload_report(self):
        """获取教师工作量报表数据"""
        query = """
        SELECT 
            t.name,
            COUNT(DISTINCT c.course_id) as course_count,
            COUNT(DISTINCT cs.student_id) as student_count
        FROM Teachers t
        LEFT JOIN Courses c ON t.teacher_id = c.teacher_id
        LEFT JOIN Course_Selections cs ON c.course_id = cs.course_id
        GROUP BY t.teacher_id, t.name
        """
        results = self.db.fetch_all(query)

        return {
            'labels': [r[0] for r in results],  # 教师名称
            'courses': [r[1] for r in results],  # 课程数
            'students': [r[2] for r in results]  # 学生数
        }

    def get_course_selection_report(self):
        """获取选课情况报表数据"""
        try:
            query = """
            SELECT 
                c.name,
                COUNT(cs.selection_id) as selection_count,
                c.max_students
            FROM Courses c
            LEFT JOIN Course_Selections cs ON c.course_id = cs.course_id
            WHERE c.semester_id = (
                SELECT semester_id FROM Semesters 
                WHERE status = 1 
                ORDER BY start_date DESC 
                LIMIT 1
            )
            GROUP BY c.course_id, c.name, c.max_students
            ORDER BY selection_count DESC
            LIMIT 10
            """
            results = self.db.fetch_all(query)
            print(f"Debug - Course selection report results: {results}")

            return {
                'labels': [row[0] for row in results],  # 课程名称
                'values': [row[1] for row in results],  # 已选人数
                'max_students': [row[2] for row in results]  # 最大人数
            }
        except Exception as e:
            print(f"Error in get_course_selection_report: {e}")
            return {'labels': [], 'values': [], 'max_students': []}

    def get_grade_distribution(self, course_id):
        """获取课程成绩分布"""
        query = """
        SELECT 
            CASE 
                WHEN score < 60 THEN '不及格'
                WHEN score < 70 THEN '60-69'
                WHEN score < 80 THEN '70-79'
                WHEN score < 90 THEN '80-89'
                ELSE '90-100'
            END as grade_range,
            COUNT(*) as count
        FROM Grades g
        JOIN Course_Selections cs ON g.selection_id = cs.selection_id
        WHERE cs.course_id = %s
        GROUP BY grade_range
        ORDER BY grade_range
        """
        results = self.db.fetch_all(query, (course_id,))

        # 确保所有分数段都有数据
        distribution = [0] * 5  # [不及格, 60-69, 70-79, 80-89, 90-100]
        ranges = ['不及格', '60-69', '70-79', '80-89', '90-100']

        for result in results:
            idx = ranges.index(result[0])
            distribution[idx] = result[1]

        return {'distribution': distribution}

    def export_teacher_workload(self):
        """导出教师工作量报表"""
        query = """
        SELECT 
            t.teacher_id,
            t.name,
            t.title,
            COUNT(DISTINCT c.course_id) as course_count,
            SUM(c.credits) as total_credits,
            COUNT(DISTINCT cs.student_id) as student_count
        FROM Teachers t
        LEFT JOIN Courses c ON t.teacher_id = c.teacher_id
        LEFT JOIN Course_Selections cs ON c.course_id = cs.course_id
        GROUP BY t.teacher_id, t.name, t.title
        """
        return self.db.fetch_all(query)

    def export_course_selection(self):
        """导出选课情况报表"""
        query = """
        SELECT 
            c.course_id,
            c.name,
            t.name as teacher,
            c.credits,
            COUNT(cs.selection_id) as selected_count,
            c.max_students,
            s.name as semester
        FROM Courses c
        JOIN Teachers t ON c.teacher_id = t.teacher_id
        JOIN Semesters s ON c.semester_id = s.semester_id
        LEFT JOIN Course_Selections cs ON c.course_id = cs.course_id
        GROUP BY c.course_id
        """
        return self.db.fetch_all(query)

    def export_grade_distribution(self, course_id):
        """导出成绩分布报表"""
        query = """
        SELECT 
            s.student_id,
            s.name as student_name,
            g.score,
            g.grade_type,
            g.input_time
        FROM Grades g
        JOIN Course_Selections cs ON g.selection_id = cs.selection_id
        JOIN Students s ON cs.student_id = s.student_id
        WHERE cs.course_id = %s
        ORDER BY g.score DESC
        """
        return self.db.fetch_all(query, (course_id,))

    def get_class_info(self, class_id):
        """获取班级信息"""
        try:
            query = """
            SELECT 
                c.class_id,
                c.name,
                m.name as major_name,
                COALESCE(co.name, '未分配') as counselor_name,
                c.grade_year
            FROM Classes c
            JOIN Majors m ON c.major_id = m.major_id
            LEFT JOIN Counselors co ON c.counselor_id = co.counselor_id
            WHERE c.class_id = %s
            """
            result = self.db.fetch_one(query, (class_id,))
            if result:
                return {
                    'class_id': result[0],
                    'name': result[1],
                    'major_name': result[2],
                    'counselor_name': result[3],
                    'grade_year': result[4]
                }
            return None
        except Exception as e:
            print(f"Error in get_class_info: {e}")
            return None

    def get_class_students(self, class_id):
        """获取班级学生列表"""
        try:
            query = """
            SELECT 
                s.student_id,
                s.name,
                s.gender,
                s.user_id,
                u.username
            FROM Students s
            JOIN Users u ON s.user_id = u.user_id
            WHERE s.class_id = %s
            ORDER BY s.student_id
            """
            results = self.db.fetch_all(query, (class_id,))
            return [
                {
                    'student_id': row[0],
                    'name': row[1],
                    'gender': row[2],
                    'user_id': row[3],
                    'username': row[4]
                }
                for row in results
            ]
        except Exception as e:
            print(f"Error in get_class_students: {e}")
            return []

    def update_student(self, student_id, name, gender):
        """更新学生信息"""
        try:
            query = """
            UPDATE Students 
            SET name = %s, gender = %s
            WHERE student_id = %s
            """
            return bool(self.db.execute_query(query, (name, gender, student_id)))
        except Exception as e:
            print(f"Error in update_student: {e}")
            return False

    def get_majors_list(self):
        """获取专业列表"""
        try:
            query = """
            SELECT 
                major_id,
                name,
                department
            FROM Majors
            ORDER BY major_id
            """
            print(f"Debug - Majors query: {query}")
            results = self.db.fetch_all(query)
            print(f"Debug - Majors results: {results}")
            return results
        except Exception as e:
            print(f"Error in get_majors_list: {e}")
            return []

    def add_major(self, name, department):
        """添加专业"""
        try:
            query = """
            INSERT INTO Majors (name, department) 
            VALUES (%s, %s)
            """
            return bool(self.db.execute_query(query, (name, department)))
        except Exception as e:
            print(f"Error in add_major: {e}")
            return False

    def update_major(self, major_id, name, department):
        """更新专业信息"""
        try:
            query = """
            UPDATE Majors 
            SET name = %s, department = %s
            WHERE major_id = %s
            """
            return bool(self.db.execute_query(query, (name, department, major_id)))
        except Exception as e:
            print(f"Error in update_major: {e}")
            return False

    def delete_major(self, major_id):
        """删除专业"""
        try:
            # 首先检查是否有关联的班级
            check_query = """
            SELECT COUNT(*) 
            FROM Classes 
            WHERE major_id = %s
            """
            count = self.db.fetch_one(check_query, (major_id,))[0]
            if count > 0:
                print(f"Cannot delete major {major_id}: has associated classes")
                return False

            query = "DELETE FROM Majors WHERE major_id = %s"
            return bool(self.db.execute_query(query, (major_id,)))
        except Exception as e:
            print(f"Error in delete_major: {e}")
            return False

    def get_students_list(self):
        """获取学生列表"""
        try:
            query = """
            SELECT 
                s.student_id,
                s.name,
                s.gender,
                COALESCE(c.name, '未分配') as class_name,
                COALESCE(m.name, '未分配') as major_name
            FROM Students s
            LEFT JOIN Classes c ON s.class_id = c.class_id
            LEFT JOIN Majors m ON c.major_id = m.major_id
            ORDER BY s.student_id
            """
            print(f"Debug - Students query: {query}")
            results = self.db.fetch_all(query)
            print(f"Debug - Students results: {results}")
            return results
        except Exception as e:
            print(f"Error in get_students_list: {e}")
            return []

    def add_student(self, name, gender, class_id):
        """添加学生"""
        try:
            # 生成学生ID
            student_id = self.generate_student_id(class_id)
            # 生成用户ID
            user_id = self.generate_user_id('student')

            # 开始事务
            self.db.start_transaction()

            try:
                # 添加用户记录
                user_query = """
                INSERT INTO Users (user_id, username, password, role)
                VALUES (%s, %s, %s, 'student')
                """
                self.db.execute_query(user_query, (user_id, student_id, '123456'))

                # 添加学生记录
                student_query = """
                INSERT INTO Students (student_id, name, gender, class_id, user_id)
                VALUES (%s, %s, %s, %s, %s)
                """
                self.db.execute_query(student_query, (student_id, name, gender, class_id, user_id))

                # 提交事务
                self.db.commit()
                return True

            except Exception as e:
                # 回滚事务
                self.db.rollback()
                print(f"Error in add_student transaction: {e}")
                return False

        except Exception as e:
            print(f"Error in add_student: {e}")
            return False

    def update_student_full(self, student_id, name, gender, class_id):
        """更新学生完整信息"""
        try:
            query = """
            UPDATE Students 
            SET name = %s, gender = %s, class_id = %s
            WHERE student_id = %s
            """
            return bool(self.db.execute_query(query, (name, gender, class_id, student_id)))
        except Exception as e:
            print(f"Error in update_student_full: {e}")
            return False

    def delete_student(self, student_id):
        """删除学生"""
        try:
            # 开始事务
            self.db.start_transaction()

            try:
                # 获取用户ID
                user_query = "SELECT user_id FROM Students WHERE student_id = %s"
                user_result = self.db.fetch_one(user_query, (student_id,))

                if not user_result:
                    return False

                user_id = user_result[0]

                # 删除学生记录
                student_query = "DELETE FROM Students WHERE student_id = %s"
                self.db.execute_query(student_query, (student_id,))

                # 删除用户记录
                user_query = "DELETE FROM Users WHERE user_id = %s"
                self.db.execute_query(user_query, (user_id,))

                # 提交事务
                self.db.commit()
                return True

            except Exception as e:
                # 回滚事务
                self.db.rollback()
                print(f"Error in delete_student transaction: {e}")
                return False

        except Exception as e:
            print(f"Error in delete_student: {e}")
            return False

    def generate_student_id(self, class_id):
        """生成学生ID"""
        try:
            query = """
            SELECT MAX(CAST(SUBSTRING(student_id, 9) AS UNSIGNED))
            FROM Students 
            WHERE class_id = %s
            """
            result = self.db.fetch_one(query, (class_id,))

            # 获取班级年级
            class_query = "SELECT grade_year FROM Classes WHERE class_id = %s"
            class_result = self.db.fetch_one(class_query, (class_id,))
            grade_year = class_result[0] if class_result else datetime.now().year

            if result and result[0]:
                new_number = result[0] + 1
            else:
                new_number = 1

            # 格式：年份(4位) + 班级ID(3位) + 序号(3位)
            return f"{grade_year}{class_id:03d}{new_number:03d}"

        except Exception as e:
            print(f"Error in generate_student_id: {e}")
            return None

    def get_classes_list(self):
        """获取班级列表"""
        try:
            query = """
                SELECT 
                    c.class_id,
                    c.name,
                    m.name as major_name,
                    COALESCE(co.name, '未分配') as counselor_name,
                    (SELECT COUNT(*) FROM Students s WHERE s.class_id = c.class_id) as student_count
                FROM Classes c
                LEFT JOIN Majors m ON c.major_id = m.major_id
                LEFT JOIN Counselors co ON c.counselor_id = co.counselor_id
                ORDER BY c.class_id
            """
            print("Debug - Classes query:", query)
            results = self.db.fetch_all(query)
            print("Debug - Classes results:", results)

            if not results:
                print("Debug - No classes found")
                return []

            return results
        except Exception as e:
            print(f"Error in get_classes_list: {e}")
            raise

    def update_class_full(self, class_id, name, major_id, counselor_id=None):
        """更新班级完整信息"""
        try:
            query = """
            UPDATE Classes 
            SET name = %s, major_id = %s, counselor_id = %s
            WHERE class_id = %s
            """
            return bool(self.db.execute_query(query, (name, major_id, counselor_id, class_id)))
        except Exception as e:
            print(f"Error in update_class_full: {e}")
            return False

    def get_counselors_list(self):
        """获取所有辅导员列表"""
        try:
            query = """
                SELECT counselor_id, name, department
                FROM Counselors
                ORDER BY counselor_id
            """
            results = self.db.fetch_all(query)
            print(f"Debug - Counselors query results: {results}")
            return results
        except Exception as e:
            print(f"Error in get_counselors_list: {e}")
            return []

    def get_teachers_list(self):
        """获取教师列表"""
        try:
            query = """
            SELECT 
                t.teacher_id,
                t.name,
                t.title,
                t.department
            FROM Teachers t
            ORDER BY t.teacher_id
            """
            print(f"Debug - Teachers query: {query}")
            results = self.db.fetch_all(query)
            print(f"Debug - Teachers results: {results}")
            return results
        except Exception as e:
            print(f"Error in get_teachers_list: {e}")
            return []

    def add_teacher(self, name, title, department):
        """添加教师"""
        try:
            # 开始事务
            self.db.start_transaction()
            try:
                # 获取最大的教师工号
                teacher_query = """
                SELECT teacher_id 
                FROM Teachers 
                WHERE teacher_id LIKE 'T%'
                ORDER BY CAST(SUBSTRING(teacher_id, 2) AS UNSIGNED) DESC 
                LIMIT 1
                """
                teacher_result = self.db.fetch_one(teacher_query)
                print(f"Debug - Last teacher ID: {teacher_result}")

                # 获取最大的用户名编号
                user_query = """
                SELECT username 
                FROM Users 
                WHERE username LIKE 'teacher_%'
                ORDER BY CAST(SUBSTRING_INDEX(username, '_', -1) AS UNSIGNED) DESC 
                LIMIT 1
                """
                user_result = self.db.fetch_one(user_query)
                print(f"Debug - Last username: {user_result}")

                # 生成新的教师工号
                if teacher_result and teacher_result[0]:
                    last_num = int(teacher_result[0][1:])  # 去掉 'T' 前缀
                    next_num = last_num + 1
                else:
                    next_num = 1

                new_teacher_id = f"T{next_num:06d}"

                # 生成新的用户ID和用户名
                if user_result and user_result[0]:
                    last_num = int(user_result[0].split('_')[1])
                    next_user_num = last_num + 1
                else:
                    next_user_num = 1

                new_user_id = f"U{next_user_num:06d}"
                new_username = f"teacher_{next_user_num:06d}"

                print(f"Debug - Generated IDs: teacher={new_teacher_id}, user={new_user_id}, username={new_username}")

                # 创建用户账号
                user_insert_query = """
                INSERT INTO Users (user_id, username, password, role)
                VALUES (%s, %s, %s, 'teacher')
                """
                password = "password123"  # 默认密码

                print(f"Debug - Creating user with ID: {new_user_id}, username: {new_username}")
                self.db.execute_query(user_insert_query, (new_user_id, new_username, password))

                # 添加教师信息
                teacher_insert_query = """
                INSERT INTO Teachers (teacher_id, user_id, name, title, department)
                VALUES (%s, %s, %s, %s, %s)
                """
                print(f"Debug - Adding teacher with ID: {new_teacher_id}")
                result = self.db.execute_query(teacher_insert_query,
                                               (new_teacher_id, new_user_id, name, title, department))

                # 提交事务
                self.db.commit()
                print("Debug - Transaction committed successfully")
                return True

            except Exception as e:
                # 回滚事务
                self.db.rollback()
                print(f"Debug - Transaction rolled back due to error: {e}")
                raise

        except Exception as e:
            print(f"Error in add_teacher: {e}")
            return False

    def get_courses_list(self):
        """获取课程列表"""
        query = """
            SELECT 
                c.course_id,
                c.name,
                c.credits,
                c.hours,  # 添加课时字段
                COALESCE(t.name, '未分配') as teacher_name,
                COALESCE(s.name, '未分配') as semester_name,
                c.max_students
            FROM Courses c
            LEFT JOIN Teachers t ON c.teacher_id = t.teacher_id
            LEFT JOIN Semesters s ON c.semester_id = s.semester_id
            ORDER BY c.course_id
        """
        results = self.db.fetch_all(query)
        print(f"Debug - Courses results: {results}")
        return results

    def get_semesters_list(self):
        """获取学期列表"""
        query = """
            SELECT 
                semester_id,
                name,
                start_date,
                end_date,
                status
            FROM Semesters
            ORDER BY start_date DESC
        """
        results = self.db.fetch_all(query)
        print(f"Debug - Semesters results: {results}")
        return [
            {
                'semester_id': row[0],
                'name': row[1],
                'start_date': row[2].strftime('%Y-%m-%d'),
                'end_date': row[3].strftime('%Y-%m-%d'),
                'status': row[4]
            }
            for row in results
        ]

    def add_semester(self, name, start_date, end_date, status):
        """添加学期"""
        try:
            query = """
            INSERT INTO Semesters (name, start_date, end_date, status)
            VALUES (%s, %s, %s, %s)
            """
            return bool(self.db.execute_query(query, (name, start_date, end_date, status)))
        except Exception as e:
            print(f"Error in add_semester: {e}")
            return False

    def get_teacher_workload_report(self):
        """获取教师工作量报表数据"""
        try:
            query = """
            SELECT 
                t.name,
                COUNT(DISTINCT c.course_id) as course_count,
                COUNT(DISTINCT cs.student_id) as student_count
            FROM Teachers t
            LEFT JOIN Courses c ON t.teacher_id = c.teacher_id
            LEFT JOIN Course_Selections cs ON c.course_id = cs.course_id
            GROUP BY t.teacher_id, t.name
            ORDER BY course_count DESC
            LIMIT 10
            """
            results = self.db.fetch_all(query)
            return {
                'labels': [row[0] for row in results],  # 教师名称
                'courses': [row[1] for row in results],  # 课程数
                'students': [row[2] for row in results]  # 学生数
            }
        except Exception as e:
            print(f"Error in get_teacher_workload_report: {e}")
            return {'labels': [], 'courses': [], 'students': []}

    def get_course_selection_report(self):
        """获取选课情况报表数据"""
        try:
            query = """
            SELECT 
                c.name,
                COUNT(cs.selection_id) as selection_count,
                c.max_students
            FROM Courses c
            LEFT JOIN Course_Selections cs ON c.course_id = cs.course_id
            WHERE c.semester_id = (
                SELECT semester_id FROM Semesters 
                WHERE status = 1 
                ORDER BY start_date DESC 
                LIMIT 1
            )
            GROUP BY c.course_id, c.name, c.max_students
            ORDER BY selection_count DESC
            LIMIT 10
            """
            results = self.db.fetch_all(query)
            print(f"Debug - Course selection report results: {results}")

            return {
                'labels': [row[0] for row in results],  # 课程名称
                'values': [row[1] for row in results],  # 已选人数
                'max_students': [row[2] for row in results]  # 最大人数
            }
        except Exception as e:
            print(f"Error in get_course_selection_report: {e}")
            return {'labels': [], 'values': [], 'max_students': []}

    def update_teacher(self, teacher_id, name, title, department):
        """更新教师信息"""
        try:
            query = """
            UPDATE Teachers 
            SET name = %s, title = %s, department = %s
            WHERE teacher_id = %s
            """
            return bool(self.db.execute_query(query, (name, title, department, teacher_id)))
        except Exception as e:
            print(f"Error in update_teacher: {e}")
            return False

    def update_semester(self, semester_id, name, start_date, end_date, status):
        """更新学期信息"""
        try:
            query = """
            UPDATE Semesters 
            SET name = %s, start_date = %s, end_date = %s, status = %s
            WHERE semester_id = %s
            """
            return bool(self.db.execute_query(query, (name, start_date, end_date, status, semester_id)))
        except Exception as e:
            print(f"Error in update_semester: {e}")
            return False

    def get_all_semesters(self):
        """获取所有学期信息"""
        try:
            query = """
            SELECT 
                semester_id,
                name,
                start_date,
                end_date,
                status
            FROM Semesters
            ORDER BY start_date DESC
            """
            print(f"Debug - Semesters query: {query}")
            results = self.db.fetch_all(query)
            print(f"Debug - Semesters results: {results}")
            return results
        except Exception as e:
            print(f"Error in get_all_semesters: {e}")
            return []

    def get_teacher_workload_report(self):
        """获取教师工作量报表数据"""
        try:
            query = """
            SELECT 
                t.name,
                COUNT(DISTINCT c.course_id) as course_count,
                COUNT(DISTINCT cs.student_id) as student_count
            FROM Teachers t
            LEFT JOIN Courses c ON t.teacher_id = c.teacher_id
            LEFT JOIN Course_Selections cs ON c.course_id = cs.course_id
            GROUP BY t.teacher_id, t.name
            ORDER BY course_count DESC
            LIMIT 10
            """
            results = self.db.fetch_all(query)
            return {
                'labels': [row[0] for row in results],  # 教师名称
                'courses': [row[1] for row in results],  # 课程数
                'students': [row[2] for row in results]  # 学生数
            }
        except Exception as e:
            print(f"Error in get_teacher_workload_report: {e}")
            return {'labels': [], 'courses': [], 'students': []}

    def get_course_selection_report(self):
        """获取选课情况报表数据"""
        try:
            query = """
            SELECT 
                c.name,
                COUNT(cs.selection_id) as selection_count,
                c.max_students
            FROM Courses c
            LEFT JOIN Course_Selections cs ON c.course_id = cs.course_id
            WHERE c.semester_id = (
                SELECT semester_id FROM Semesters 
                WHERE status = 1 
                ORDER BY start_date DESC 
                LIMIT 1
            )
            GROUP BY c.course_id, c.name, c.max_students
            ORDER BY selection_count DESC
            LIMIT 10
            """
            results = self.db.fetch_all(query)
            print(f"Debug - Course selection report results: {results}")

            return {
                'labels': [row[0] for row in results],  # 课程名称
                'values': [row[1] for row in results],  # 已选人数
                'max_students': [row[2] for row in results]  # 最大人数
            }
        except Exception as e:
            print(f"Error in get_course_selection_report: {e}")
            return {'labels': [], 'values': [], 'max_students': []}

    def get_teacher_by_id(self, teacher_id):
        query = """
            SELECT teacher_id, name, title, department
            FROM Teachers
            WHERE teacher_id = %s
        """
        return self.db.fetch_one(query, (teacher_id,))

    def delete_teacher(self, teacher_id):
        query = "DELETE FROM Teachers WHERE teacher_id = %s"
        return self.db.execute_query(query, (teacher_id,))

    def get_course_by_id(self, course_id):
        """获取课程信息"""
        query = """
            SELECT 
                course_id,
                name,
                credits,
                hours,
                teacher_id,
                semester_id,
                max_students
            FROM Courses
            WHERE course_id = %s
        """
        result = self.db.fetch_one(query, (course_id,))
        if result:
            return {
                'course_id': result[0],
                'name': result[1],
                'credits': result[2],
                'hours': result[3],
                'teacher_id': result[4],
                'semester_id': result[5],
                'max_students': result[6]
            }
        return None

    def delete_course(self, course_id):
        query = "DELETE FROM Courses WHERE course_id = %s"
        return self.db.execute_query(query, (course_id,))

    def get_class_by_id(self, class_id):
        query = """
            SELECT class_id, name, major_id, counselor_id
            FROM Classes
            WHERE class_id = %s
        """
        return self.db.fetch_one(query, (class_id,))

    def get_class_students(self, class_id):
        query = """
            SELECT s.student_id, s.name, s.gender
            FROM Students s
            WHERE s.class_id = %s
        """
        return self.db.fetch_all(query, (class_id,))

    def get_major_by_id(self, major_id):
        """获取专业信息"""
        query = """
            SELECT major_id, name, department
            FROM Majors
            WHERE major_id = %s
        """
        return self.db.fetch_one(query, (major_id,))

    def add_major(self, name, department):
        """添加专业"""
        try:
            query = """
            INSERT INTO Majors (name, department) 
            VALUES (%s, %s)
            """
            return bool(self.db.execute_query(query, (name, department)))
        except Exception as e:
            print(f"Error in add_major: {e}")
            return False

    def update_major(self, major_id, name=None, department=None):
        """更新专业信息"""
        try:
            updates = []
            params = []
            if name:
                updates.append("name = %s")
                params.append(name)
            if department:
                updates.append("department = %s")
                params.append(department)

            if not updates:
                return True

            query = f"UPDATE Majors SET {', '.join(updates)} WHERE major_id = %s"
            params.append(major_id)
            return bool(self.db.execute_query(query, tuple(params)))
        except Exception as e:
            print(f"Error in update_major: {e}")
            return False

    def delete_major(self, major_id):
        """删除专业"""
        try:
            query = "DELETE FROM Majors WHERE major_id = %s"
            return bool(self.db.execute_query(query, (major_id,)))
        except Exception as e:
            print(f"Error in delete_major: {e}")
            return False

    def generate_course_id(self):
        """生成课程ID"""
        query = """
            SELECT course_id 
            FROM Courses 
            WHERE course_id LIKE 'C%'
            ORDER BY course_id DESC 
            LIMIT 1
        """
        result = self.db.fetch_one(query)

        if result and result[0]:
            last_num = int(result[0][1:])  # 去掉 'C' 前缀
            next_num = last_num + 1
        else:
            next_num = 1

        return f"C{next_num:03d}"

    def get_semester_by_id(self, semester_id):
        """获取学期信息"""
        query = """
            SELECT semester_id, name, start_date, end_date, status
            FROM Semesters
            WHERE semester_id = %s
        """
        return self.db.fetch_one(query, (semester_id,))

    def delete_semester(self, semester_id):
        """删除学期"""
        query = "DELETE FROM Semesters WHERE semester_id = %s"
        return bool(self.db.execute_query(query, (semester_id,)))

    def export_report(self, report_type):
        """导出报表"""
        try:
            if report_type == 'teacher_workload':
                query = """
                SELECT 
                    t.name as '教师姓名',
                    t.title as '职称',
                    t.department as '院系',
                    COUNT(DISTINCT c.course_id) as '授课数量',
                    COUNT(DISTINCT cs.student_id) as '学生总数'
                FROM Teachers t
                LEFT JOIN Courses c ON t.teacher_id = c.teacher_id
                LEFT JOIN Course_Selections cs ON c.course_id = cs.course_id
                GROUP BY t.teacher_id, t.name, t.title, t.department
                ORDER BY COUNT(DISTINCT c.course_id) DESC
                """
                columns = ['教师姓名', '职称', '院系', '授课数量', '学生总数']
            elif report_type == 'course_selection':
                query = """
                SELECT 
                    c.course_id as '课程编号',
                    c.name as '课程名称',
                    t.name as '授课教师',
                    c.max_students as '最大人数',
                    COUNT(cs.selection_id) as '已选人数',
                    ROUND(COUNT(cs.selection_id) * 100.0 / c.max_students, 2) as '选课率'
                FROM Courses c
                LEFT JOIN Teachers t ON c.teacher_id = t.teacher_id
                LEFT JOIN Course_Selections cs ON c.course_id = cs.course_id
                GROUP BY c.course_id, c.name, t.name, c.max_students
                ORDER BY COUNT(cs.selection_id) DESC
                """
                columns = ['课程编号', '课程名称', '授课教师', '最大人数', '已选人数', '选课率']
            else:
                raise ValueError("不支持的报表类型")

            results = self.db.fetch_all(query)
            print(f"Debug - Export report results: {results}")
            return columns, results

        except Exception as e:
            print(f"Error in export_report: {e}")
            return None, None