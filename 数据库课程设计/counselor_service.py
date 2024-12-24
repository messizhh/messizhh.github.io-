from db_connection import DatabaseConnection


class CounselorService:
    def __init__(self):
        self.db = DatabaseConnection()

    def get_student_grades(self, student_id):
        query = """
        SELECT 
            c.name as course_name,
            g.score,
            g.grade_type,
            g.input_time
        FROM Course_Selections cs
        JOIN Courses c ON cs.course_id = c.course_id
        LEFT JOIN Grades g ON cs.selection_id = g.selection_id
        WHERE cs.student_id = %s
        """
        return self.db.fetch_all(query, (student_id,))

    def add_student_focus(self, student_id, counselor_id, reason):
        query = """
        INSERT INTO Student_Focus (student_id, counselor_id, reason)
        VALUES (%s, %s, %s)
        """
        return bool(self.db.execute_query(query, (student_id, counselor_id, reason)))

    def get_managed_classes(self, counselor_id):
        """获取辅导员管理的班级列表"""
        query = """
        SELECT 
            c.class_id,
            c.name as class_name,
            m.name as major_name,
            COUNT(DISTINCT s.student_id) as student_count,
            c.grade_year
        FROM Classes c
        JOIN Counselors co ON c.counselor_id = co.counselor_id
        LEFT JOIN Majors m ON c.major_id = m.major_id
        LEFT JOIN Students s ON c.class_id = s.class_id
        WHERE co.counselor_id = %s
        GROUP BY c.class_id, c.name, m.name, c.grade_year
        ORDER BY c.grade_year DESC, c.name
        """
        try:
            print(f"Debug - Getting classes for counselor: {counselor_id}")
            results = self.db.fetch_all(query, (counselor_id,))
            print(f"Debug - Found classes: {results}")
            return results
        except Exception as e:
            print(f"Error in get_managed_classes: {e}")
            return []

    def get_class_grades(self, class_id, semester_id=None):
        """获取班级学生成绩"""
        params = [class_id]
        semester_condition = ""
        if semester_id:
            semester_condition = "AND cs.semester_id = %s"
            params.append(semester_id)

        query = f"""
        SELECT 
            s.student_id,
            s.name as student_name,
            c.name as course_name,
            g.score,
            CASE
                WHEN g.score >= 90 THEN 4.0
                WHEN g.score >= 85 THEN 3.7
                WHEN g.score >= 82 THEN 3.3
                WHEN g.score >= 78 THEN 3.0
                WHEN g.score >= 75 THEN 2.7
                WHEN g.score >= 72 THEN 2.3
                WHEN g.score >= 68 THEN 2.0
                WHEN g.score >= 64 THEN 1.5
                WHEN g.score >= 60 THEN 1.0
                ELSE 0
            END as gpa,
            g.grade_type,
            sem.name as semester_name
        FROM Students s
        JOIN Course_Selections cs ON s.student_id = cs.student_id
        JOIN Courses c ON cs.course_id = c.course_id
        JOIN Semesters sem ON cs.semester_id = sem.semester_id
        LEFT JOIN Grades g ON cs.selection_id = g.selection_id
        WHERE s.class_id = %s {semester_condition}
        ORDER BY s.student_id, sem.start_date
        """
        return self.db.fetch_all(query, tuple(params))

    def get_class_stats(self, class_id):
        """获取班级成绩统计信息"""
        query = """
        WITH StudentStats AS (
            SELECT 
                s.student_id,
                COUNT(DISTINCT cs.course_id) as total_courses,
                COUNT(DISTINCT CASE WHEN g.score >= 60 THEN cs.course_id END) as passed_courses,
                AVG(g.score) as avg_score
            FROM Students s
            LEFT JOIN Course_Selections cs ON s.student_id = cs.student_id AND cs.status = 1
            LEFT JOIN Grades g ON cs.selection_id = g.selection_id
            WHERE s.class_id = %s
            GROUP BY s.student_id
        )
        SELECT
            COUNT(student_id) as total_students,
            ROUND(AVG(COALESCE(avg_score, 0)), 2) as class_avg_score,
            COUNT(CASE WHEN COALESCE(avg_score, 0) >= 60 THEN 1 END) as passing_students,
            SUM(COALESCE(total_courses, 0)) as total_course_selections,
            SUM(COALESCE(passed_courses, 0)) as total_passed_courses
        FROM StudentStats
        """
        try:
            print(f"Debug - Getting stats for class: {class_id}")
            result = self.db.fetch_one(query, (class_id,))
            print(f"Debug - Class stats: {result}")
            return result
        except Exception as e:
            print(f"Error in get_class_stats: {e}")
            return None

    def get_failing_students(self, class_id, semester_id=None):
        """获取不及格学生名单"""
        params = [class_id]
        semester_condition = ""
        if semester_id:
            semester_condition = "AND cs.semester_id = %s"
            params.append(semester_id)

        query = f"""
        SELECT DISTINCT
            s.student_id,
            s.name as student_name,
            c.name as course_name,
            g.score
        FROM Students s
        JOIN Course_Selections cs ON s.student_id = cs.student_id
        JOIN Courses c ON cs.course_id = c.course_id
        JOIN Grades g ON cs.selection_id = g.selection_id
        WHERE s.class_id = %s 
        AND g.score < 60 
        {semester_condition}
        ORDER BY s.student_id
        """
        return self.db.fetch_all(query, tuple(params))

    def get_student_detail(self, student_id):
        """获取学生详细信息"""
        query = """
        SELECT 
            s.student_id,
            s.name,
            s.gender,
            c.name as class_name,
            m.name as major_name,
            s.enrollment_year
        FROM Students s
        JOIN Classes c ON s.class_id = c.class_id
        JOIN Majors m ON c.major_id = m.major_id
        WHERE s.student_id = %s
        """
        return self.db.fetch_one(query, (student_id,))

    def get_student_grade_trend(self, student_id):
        """获取学生成绩趋势"""
        query = """
        SELECT 
            sem.name as semester,
            AVG(g.score) as avg_score
        FROM Course_Selections cs
        JOIN Semesters sem ON cs.semester_id = sem.semester_id
        JOIN Grades g ON cs.selection_id = g.selection_id
        WHERE cs.student_id = %s
        GROUP BY sem.semester_id, sem.name
        ORDER BY sem.start_date
        """
        return self.db.fetch_all(query, (student_id,))

    def export_class_grades(self, class_id, semester_id=None):
        """导出班级成绩单"""
        grades = self.get_class_grades(class_id, semester_id)
        if not grades:
            return None

        # 转换成绩类型显示
        grade_types = {
            'final': '期末考试',
            'makeup': '补考',
            'resit': '重修'
        }

        formatted_grades = []
        for grade in grades:
            formatted_grade = list(grade)
            if formatted_grade[5]:  # grade_type
                formatted_grade[5] = grade_types.get(formatted_grade[5], formatted_grade[5])
            formatted_grades.append(formatted_grade)

        return formatted_grades

    def get_semesters(self):
        """获取所有学期列表"""
        query = """
        SELECT 
            semester_id,
            name,
            start_date,
            end_date
        FROM Semesters
        ORDER BY start_date DESC
        """
        return self.db.fetch_all(query)

    def get_class_info(self, class_id):
        """获取班级基本信息"""
        query = """
        SELECT 
            c.class_id,
            c.name as class_name,
            m.name as major_name,
            c.grade_year,
            COUNT(DISTINCT s.student_id) as student_count,
            co.name as counselor_name
        FROM Classes c
        LEFT JOIN Majors m ON c.major_id = m.major_id
        LEFT JOIN Counselors co ON c.counselor_id = co.counselor_id
        LEFT JOIN Students s ON c.class_id = s.class_id
        WHERE c.class_id = %s
        GROUP BY c.class_id, c.name, m.name, c.grade_year, co.name
        """
        try:
            print(f"Debug - Getting info for class: {class_id}")
            result = self.db.fetch_one(query, (class_id,))
            print(f"Debug - Class info: {result}")
            return result
        except Exception as e:
            print(f"Error in get_class_info: {e}")
            return None

    def get_class_students(self, class_id):
        """获取班级学生列表"""
        query = """
        SELECT 
            s.student_id,
            s.name,
            COUNT(DISTINCT cs.course_id) as course_count,
            COUNT(CASE WHEN g.score < 60 THEN 1 END) as failed_courses,
            AVG(g.score) as avg_score,
            COALESCE(sf.focus_id IS NOT NULL, false) as is_focused
        FROM Students s
        LEFT JOIN Course_Selections cs ON s.student_id = cs.student_id
        LEFT JOIN Grades g ON cs.selection_id = g.selection_id
        LEFT JOIN Student_Focus sf ON s.student_id = sf.student_id
        WHERE s.class_id = %s
        GROUP BY s.student_id, s.name, sf.focus_id
        ORDER BY s.student_id
        """
        try:
            print(f"Debug - Getting students for class: {class_id}")
            results = self.db.fetch_all(query, (class_id,))
            print(f"Debug - Found students: {results}")
            return results
        except Exception as e:
            print(f"Error in get_class_students: {e}")
            return []

    def get_student_grades_detail(self, student_id):
        """获取学生成绩详情"""
        query = """
        SELECT 
            c.name as course_name,
            g.score,
            CASE
                WHEN g.score >= 90 THEN 4.0
                WHEN g.score >= 85 THEN 3.7
                WHEN g.score >= 82 THEN 3.3
                WHEN g.score >= 78 THEN 3.0
                WHEN g.score >= 75 THEN 2.7
                WHEN g.score >= 72 THEN 2.3
                WHEN g.score >= 68 THEN 2.0
                WHEN g.score >= 64 THEN 1.5
                WHEN g.score >= 60 THEN 1.0
                ELSE 0
            END as gpa,
            g.grade_type,
            sem.name as semester_name
        FROM Course_Selections cs
        JOIN Courses c ON cs.course_id = c.course_id
        JOIN Semesters sem ON cs.semester_id = sem.semester_id
        LEFT JOIN Grades g ON cs.selection_id = g.selection_id
        WHERE cs.student_id = %s
        ORDER BY sem.start_date DESC, c.name
        """
        results = self.db.fetch_all(query, (student_id,))

        # 转换为字典列表以适配DataTables
        grades = []
        for row in results:
            grades.append({
                'course_name': row[0],
                'score': row[1],
                'gpa': row[2],
                'grade_type': row[3],
                'semester_name': row[4]
            })
        return grades

    def log_action(self, user_id, action_type, target_type, target_id, details):
        """记录辅导员操作日志"""
        query = """
        INSERT INTO System_Logs (user_id, action_type, target_type, target_id, details)
        VALUES (%s, %s, %s, %s, %s)
        """
        return bool(self.db.execute_query(query,
                                          (user_id, action_type, target_type, target_id, details)))

    def get_counselor_classes(self, counselor_id):
        """获取辅导员负责的班级列表"""
        try:
            query = """
            SELECT 
                c.class_id,
                c.name as class_name,
                m.name as major_name,
                c.grade_year,
                COUNT(DISTINCT s.student_id) as student_count
            FROM Classes c
            LEFT JOIN Teachers t ON c.counselor_id = t.teacher_id
            LEFT JOIN Majors m ON c.major_id = m.major_id
            LEFT JOIN Students s ON c.class_id = s.class_id
            WHERE t.teacher_id = %s
            GROUP BY c.class_id, c.name, m.name, c.grade_year
            ORDER BY c.grade_year DESC, c.name
            """
            print(f"Debug - Executing query for counselor_id: {counselor_id}")  # 调试输出
            results = self.db.fetch_all(query, (counselor_id,))
            print(f"Debug - Query results: {results}")  # 调试输出

            classes = [
                {
                    'class_id': row[0],
                    'class_name': row[1],
                    'major_name': row[2],
                    'grade_year': row[3],
                    'student_count': row[4]
                }
                for row in results
            ]
            print(f"Debug - Formatted classes: {classes}")  # 调试输出
            return classes

        except Exception as e:
            print(f"Error in get_counselor_classes: {e}")
            return []

    def get_student_courses(self, student_id):
        """获取学生的选课和成绩详情"""
        query = """
        SELECT 
            c.course_id,
            c.name as course_name,
            t.name as teacher_name,
            g.score,
            g.grade_type,
            g.input_time
        FROM Course_Selections cs
        JOIN Courses c ON cs.course_id = c.course_id
        JOIN Teachers t ON c.teacher_id = t.teacher_id
        LEFT JOIN Grades g ON cs.selection_id = g.selection_id
        WHERE cs.student_id = %s AND cs.status = 1
        ORDER BY g.input_time DESC
        """
        return self.db.fetch_all(query, (student_id,))

    def toggle_student_risk_status(self, student_id, counselor_id):
        """切换学生的重点关注状态"""
        try:
            # 首先检查是否已经关注
            check_query = """
            SELECT focus_id 
            FROM Student_Focus 
            WHERE student_id = %s AND counselor_id = %s
            """
            focus = self.db.fetch_one(check_query, (student_id, counselor_id))

            if focus:
                # 如果已关注，则取消关注
                delete_query = """
                DELETE FROM Student_Focus 
                WHERE student_id = %s AND counselor_id = %s
                """
                self.db.execute_query(delete_query, (student_id, counselor_id))
            else:
                # 如果未关注，则添加关注
                insert_query = """
                INSERT INTO Student_Focus (student_id, counselor_id, reason)
                VALUES (%s, %s, '辅导员关注')
                """
                self.db.execute_query(insert_query, (student_id, counselor_id))

            return True
        except Exception as e:
            print(f"Error in toggle_student_risk_status: {e}")
            return False

    def get_class_grade_distribution(self, class_id):
        """获取班级成绩分布"""
        query = """
        SELECT 
            CASE 
                WHEN score < 60 THEN '不及格'
                WHEN score < 70 THEN '及格'
                WHEN score < 80 THEN '中等'
                WHEN score < 90 THEN '良好'
                ELSE '优秀'
            END as grade_level,
            COUNT(*) as count
        FROM Course_Selections cs
        JOIN Students s ON cs.student_id = s.student_id
        JOIN Grades g ON cs.selection_id = g.selection_id
        WHERE s.class_id = %s AND cs.status = 1
        GROUP BY 
            CASE 
                WHEN score < 60 THEN '不及格'
                WHEN score < 70 THEN '及格'
                WHEN score < 80 THEN '中等'
                WHEN score < 90 THEN '良好'
                ELSE '优秀'
            END
        ORDER BY MIN(score)
        """
        try:
            print(f"Debug - Getting grade distribution for class: {class_id}")
            results = self.db.fetch_all(query, (class_id,))
            print(f"Debug - Grade distribution: {results}")
            return results
        except Exception as e:
            print(f"Error in get_class_grade_distribution: {e}")
            return []

    def export_class_report(self, class_id):
        """导出班级成绩报表"""
        query = """
        SELECT 
            s.student_id as '学号',
            s.name as '姓名',
            COUNT(DISTINCT cs.course_id) as '选课数',
            ROUND(AVG(g.score), 2) as '平均分',
            COUNT(CASE WHEN g.score < 60 THEN 1 END) as '不及格课程数',
            CASE WHEN s.at_risk THEN '是' ELSE '否' END as '重点关注'
        FROM Students s
        LEFT JOIN Course_Selections cs ON s.student_id = cs.student_id AND cs.status = 1
        LEFT JOIN Grades g ON cs.selection_id = g.selection_id
        WHERE s.class_id = %s
        GROUP BY s.student_id, s.name, s.at_risk
        ORDER BY s.student_id
        """
        return self.db.fetch_all(query, (class_id,))