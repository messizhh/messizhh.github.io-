from db_connection import DatabaseConnection


class TeacherService:
    def __init__(self):
        self.db = DatabaseConnection()

    def query_teaching_courses(self, teacher_id):
        """获取教师教授的课程"""
        print(f"Debug - Getting courses for teacher: {teacher_id}")  # 添加调试输出

        query = """
        SELECT 
            c.course_id as id,
            CONCAT(c.name, ' (', c.course_id, ')') as text
        FROM Courses c
        WHERE c.teacher_id = %s
        """
        courses = self.db.fetch_all(query, (teacher_id,))
        print(f"Debug - Found courses: {courses}")  # 添加调试输出

        return [{'id': course[0], 'text': course[1]} for course in courses]

    def get_course_students(self, course_id):
        """获取课程的学生列表"""
        query = """
        SELECT 
            s.student_id,
            s.name as student_name,
            g.score,
            g.grade_type,
            g.input_time
        FROM Course_Selections cs
        JOIN Students s ON cs.student_id = s.student_id
        LEFT JOIN Grades g ON cs.selection_id = g.selection_id
        WHERE cs.course_id = %s AND cs.status = 1
        ORDER BY s.student_id
        """
        results = self.db.fetch_all(query, (course_id,))

        # 转换为字典列表以适配DataTables
        students = []
        for row in results:
            students.append({
                'student_id': row[0],
                'student_name': row[1],
                'score': float(row[2]) if row[2] else None,
                'grade_type': row[3] if row[3] else 'final',
                'input_time': row[4].strftime('%Y-%m-%d %H:%M:%S') if row[4] else None
            })
        return students

    def input_grades(self, course_id, student_id, score):
        """录入成绩"""
        try:
            # 获取选课记录ID
            selection_query = """
            SELECT selection_id 
            FROM Course_Selections 
            WHERE course_id = %s AND student_id = %s AND status = 1
            """
            selection = self.db.fetch_one(selection_query, (course_id, student_id))
            if not selection:
                return False

            # 检查是否已有成绩
            check_query = """
            SELECT grade_id FROM Grades 
            WHERE selection_id = %s
            """
            existing = self.db.fetch_one(check_query, (selection[0],))

            if existing:
                # 更新成绩
                update_query = """
                UPDATE Grades 
                SET score = %s, input_time = NOW()
                WHERE selection_id = %s
                """
                return bool(self.db.execute_query(update_query, (score, selection[0])))
            else:
                # 插入新成绩
                insert_query = """
                INSERT INTO Grades (selection_id, score, grade_type, input_time)
                VALUES (%s, %s, 'regular', NOW())
                """
                return bool(self.db.execute_query(insert_query, (selection[0], score)))

        except Exception as e:
            print(f"Error in input_grades: {e}")
            return False

    def analyze_grades(self, course_id):
        """分析课程成绩"""
        try:
            print(f"Debug - Analyzing grades for course: {course_id}")

            # 首先检查是否有成绩记录
            check_query = """
            SELECT COUNT(*)
            FROM Course_Selections cs
            JOIN Grades g ON cs.selection_id = g.selection_id
            WHERE cs.course_id = %s AND cs.status = 1
            """
            count = self.db.fetch_one(check_query, (course_id,))
            print(f"Debug - Found {count[0]} grade records")

            if not count or count[0] == 0:
                print("Debug - No grades found")
                return None

            # 获取成绩统计
            stats_query = """
            SELECT 
                COUNT(*) as total_students,
                ROUND(AVG(g.score), 2) as average_score,
                MAX(g.score) as highest_score,
                MIN(g.score) as lowest_score,
                SUM(CASE WHEN g.score >= 60 THEN 1 ELSE 0 END) as passed_count
            FROM Course_Selections cs
            JOIN Grades g ON cs.selection_id = g.selection_id
            WHERE cs.course_id = %s AND cs.status = 1
            """
            stats = self.db.fetch_one(stats_query, (course_id,))
            print(f"Debug - Stats result: {stats}")

            if not stats:
                print("Debug - Failed to get stats")
                return None

            # 获取所有成绩用于分布统计
            grades_query = """
            SELECT g.score
            FROM Course_Selections cs
            JOIN Grades g ON cs.selection_id = g.selection_id
            WHERE cs.course_id = %s AND cs.status = 1
            ORDER BY g.score
            """
            grades = self.db.fetch_all(grades_query, (course_id,))
            print(f"Debug - Grades result: {grades}")

            return {
                'total': stats[0],
                'average': float(stats[1]) if stats[1] else 0,
                'highest': float(stats[2]) if stats[2] else 0,
                'lowest': float(stats[3]) if stats[3] else 0,
                'pass_count': stats[4] or 0,
                'grades': [float(g[0]) for g in grades]
            }

        except Exception as e:
            print(f"Error in analyze_grades: {e}")
            return None

    def get_course_grades(self, course_id):
        """获取课程所有学生的成绩"""
        query = """
        SELECT 
            s.student_id,
            s.name as student_name,
            g.score,
            g.grade_type,
            g.input_time
        FROM Course_Selections cs
        JOIN Students s ON cs.student_id = s.student_id
        LEFT JOIN Grades g ON cs.selection_id = g.selection_id
        WHERE cs.course_id = %s
        ORDER BY s.student_id
        """
        return self.db.fetch_all(query, (course_id,))

    def get_course_stats(self, course_id):
        """获取课程成绩统计信息"""
        grades = self.get_course_grades(course_id)
        if not grades:
            return None

        scores = [g[2] for g in grades if g[2] is not None]  # 过滤掉未录入的成绩
        if not scores:
            return None

        # 计算基本统计数据
        stats = {
            'total': len(scores),
            'average': sum(scores) / len(scores),
            'max': max(scores),
            'min': min(scores),
            'pass_count': sum(1 for s in scores if s >= 60),
            'pass_rate': sum(1 for s in scores if s >= 60) / len(scores)
        }

        # 计算成绩分布
        distribution = [0] * 5  # [0-59, 60-69, 70-79, 80-89, 90-100]
        for score in scores:
            if score < 60:
                distribution[0] += 1
            elif score < 70:
                distribution[1] += 1
            elif score < 80:
                distribution[2] += 1
            elif score < 90:
                distribution[3] += 1
            else:
                distribution[4] += 1
        stats['distribution'] = distribution

        # 计算成绩趋势
        query = """
        SELECT 
            DATE(g.input_time) as date,
            AVG(g.score) as avg_score
        FROM Course_Selections cs
        JOIN Grades g ON cs.selection_id = g.selection_id
        WHERE cs.course_id = %s
        GROUP BY DATE(g.input_time)
        ORDER BY date
        """
        trend_data = self.db.fetch_all(query, (course_id,))
        stats['trend'] = {
            'dates': [str(row[0]) for row in trend_data],
            'averages': [float(row[1]) for row in trend_data]
        }

        return stats

    def update_grade(self, course_id, student_id, score, grade_type):
        """更新学生成绩"""
        query = """
        UPDATE Grades g
        JOIN Course_Selections cs ON g.selection_id = cs.selection_id
        SET g.score = %s, g.grade_type = %s, g.input_time = CURRENT_TIMESTAMP
        WHERE cs.course_id = %s AND cs.student_id = %s
        """
        return bool(self.db.execute_query(query, (score, grade_type, course_id, student_id)))

    def export_course_grades(self, course_id):
        """导出课程成绩"""
        query = """
        SELECT 
            s.student_id as '学号',
            s.name as '姓名',
            c.name as '课程名称',
            g.score as '成绩',
            g.grade_type as '考试类型',
            g.input_time as '录入时间'
        FROM Course_Selections cs
        JOIN Students s ON cs.student_id = s.student_id
        JOIN Courses c ON cs.course_id = c.course_id
        LEFT JOIN Grades g ON cs.selection_id = g.selection_id
        WHERE cs.course_id = %s
        ORDER BY s.student_id
        """
        return self.db.fetch_all(query, (course_id,))

    def get_course_info(self, course_id):
        """获取课程基本信息"""
        query = """
        SELECT 
            c.course_id,
            c.name,
            c.credits,
            c.hours,
            t.name as teacher_name,
            s.name as semester_name,
            c.max_students,
            (
                SELECT COUNT(*)
                FROM Course_Selections cs
                WHERE cs.course_id = c.course_id AND cs.status = 1
            ) as student_count
        FROM Courses c
        JOIN Teachers t ON c.teacher_id = t.teacher_id
        JOIN Semesters s ON c.semester_id = s.semester_id
        WHERE c.course_id = %s
        """
        try:
            result = self.db.fetch_one(query, (course_id,))
            print(f"Debug - Course info: {result}")  # 添加调试输出
            return result
        except Exception as e:
            print(f"Error in get_course_info: {e}")
            return None

    def get_teaching_courses(self, teacher_id):
        """获取教师教授的所有课程详细信息"""
        print(f"Debug - Getting courses for teacher_id: {teacher_id}")  # 添加调试输出

        query = """
        SELECT 
            c.course_id,
            c.name,
            c.credits,
            c.hours,
            c.max_students,
            COUNT(DISTINCT cs.selection_id) as student_count
        FROM Courses c
        LEFT JOIN Course_Selections cs ON c.course_id = cs.course_id AND cs.status = 1
        WHERE c.teacher_id = %s
        GROUP BY c.course_id, c.name, c.credits, c.hours, c.max_students
        """
        try:
            results = self.db.fetch_all(query, (teacher_id,))
            print(f"Debug - Query results: {results}")  # 添加调试输出
            return {'data': results}
        except Exception as e:
            print(f"Error in get_teaching_courses: {e}")  # 添加错误输出
            return {'data': []}

    def get_course_students_detail(self, course_id):
        """获取课程学生的详细信息"""
        print(f"Debug - Fetching students for course_id: {course_id}")  # 添加调试输出

        query = """
        SELECT 
            s.student_id,
            s.name,
            cl.name as class_name,
            m.name as major_name,
            g.score
        FROM Course_Selections cs
        JOIN Students s ON cs.student_id = s.student_id
        JOIN Classes cl ON s.class_id = cl.class_id
        JOIN Majors m ON cl.major_id = m.major_id
        LEFT JOIN Grades g ON cs.selection_id = g.selection_id
        WHERE cs.course_id = %s AND cs.status = 1
        ORDER BY s.student_id
        """
        try:
            results = self.db.fetch_all(query, (course_id,))
            print(f"Debug - Query results: {results}")  # 添加调试输出
            return results
        except Exception as e:
            print(f"Error in get_course_students_detail: {e}")  # 添加错误输出
            raise

    def input_grade(self, course_id, student_id, score, grade_type):
        """录入或更新学生成绩"""
        try:
            print(f"Debug - Input grade: course={course_id}, student={student_id}, score={score}, type={grade_type}")

            # 验证 grade_type
            valid_grade_types = ['final', 'makeup', 'resit']
            if grade_type not in valid_grade_types:
                raise ValueError(f"无效的考试类型。必须是以下之一: {', '.join(valid_grade_types)}")

            # 检查选课记录
            check_query = """
            SELECT selection_id 
            FROM Course_Selections 
            WHERE course_id = %s AND student_id = %s AND status = 1
            """
            selection = self.db.fetch_one(check_query, (course_id, student_id))
            print(f"Debug - Selection record: {selection}")

            if not selection:
                print("Debug - No valid selection record found")
                raise ValueError("未找到有效的选课记录")

            # 检查是否已有成绩记录
            grade_query = """
            SELECT grade_id
            FROM Grades 
            WHERE selection_id = %s
            """
            grade = self.db.fetch_one(grade_query, (selection[0],))
            print(f"Debug - Existing grade record: {grade}")

            try:
                self.db.execute_query("START TRANSACTION")

                if grade:
                    # 更新现有成绩
                    update_query = """
                    UPDATE Grades 
                    SET score = %s, 
                        grade_type = %s, 
                        input_time = CURRENT_TIMESTAMP
                    WHERE selection_id = %s
                    """
                    params = (score, grade_type, selection[0])
                    print(f"Debug - Update query params: {params}")  # 添加参数调试
                    result = bool(self.db.execute_query(update_query, params))
                    print(f"Debug - Update grade result: {result}")

                    if not result:
                        raise Exception("更新成绩失败")
                else:
                    # 插入新成绩
                    insert_query = """
                    INSERT INTO Grades (
                        selection_id, 
                        score, 
                        grade_type, 
                        input_time
                    ) VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                    """
                    params = (selection[0], score, grade_type)
                    print(f"Debug - Insert query params: {params}")  # 添加参数调试
                    result = bool(self.db.execute_query(insert_query, params))
                    print(f"Debug - Insert grade result: {result}")

                    if not result:
                        raise Exception("插入成绩失败")

                self.db.execute_query("COMMIT")
                return True

            except Exception as e:
                self.db.execute_query("ROLLBACK")
                print(f"Error in grade operation: {e}")
                raise

        except Exception as e:
            print(f"Error in input_grade: {e}")
            raise ValueError(str(e))

    def log_action(self, user_id, action_type, target_type, target_id, details):
        """记录教师操作日志"""
        query = """
        INSERT INTO System_Logs (user_id, action_type, target_type, target_id, details)
        VALUES (%s, %s, %s, %s, %s)
        """
        return bool(self.db.execute_query(query,
                                          (user_id, action_type, target_type, target_id, details)))

    def get_course_students_export(self, course_id):
        """获取课程学生信息用于导出"""
        query = """
        SELECT 
            s.student_id as '学号',
            s.name as '姓名',
            cl.name as '班级',
            m.name as '专业',
            g.score as '成绩',
            g.grade_type as '考试类型',
            g.input_time as '录入时间'
        FROM Course_Selections cs
        JOIN Students s ON cs.student_id = s.student_id
        JOIN Classes cl ON s.class_id = cl.class_id
        JOIN Majors m ON cl.major_id = m.major_id
        LEFT JOIN Grades g ON cs.selection_id = g.selection_id
        WHERE cs.course_id = %s
        ORDER BY s.student_id
        """
        try:
            results = self.db.fetch_all(query, (course_id,))

            # 处理考试类型的显示
            grade_types = {
                'final': '期末考试',
                'makeup': '补考',
                'resit': '重修'
            }

            # 转换数据格式
            formatted_results = []
            for row in results:
                formatted_row = list(row)
                # 转换考试类型显示
                if formatted_row[5]:  # grade_type
                    formatted_row[5] = grade_types.get(formatted_row[5], formatted_row[5])
                # 格式化时间
                if formatted_row[6]:  # input_time
                    formatted_row[6] = formatted_row[6].strftime('%Y-%m-%d %H:%M:%S')
                formatted_results.append(formatted_row)

            return formatted_results

        except Exception as e:
            print(f"Error in get_course_students_export: {e}")
            return None

    def get_course_grades_detail(self, course_id):
        """获取课程成绩详细信息"""
        query = """
        SELECT 
            s.student_id,
            s.name as student_name,
            g.score,
            g.grade_type,
            g.input_time
        FROM Course_Selections cs
        JOIN Students s ON cs.student_id = s.student_id
        LEFT JOIN Grades g ON cs.selection_id = g.selection_id
        WHERE cs.course_id = %s AND cs.status = 1
        ORDER BY s.student_id
        """
        results = self.db.fetch_all(query, (course_id,))

        # 转换为字典列表以适配DataTables
        grades = []
        for row in results:
            grades.append({
                'student_id': row[0],
                'student_name': row[1],
                'score': float(row[2]) if row[2] else None,
                'grade_type': row[3] if row[3] else 'final',
                'input_time': row[4].strftime('%Y-%m-%d %H:%M:%S') if row[4] else None
            })
        return grades

    def get_teacher_courses(self, teacher_id):
        """获取教师的课程信息"""
        query = """
        SELECT 
            c.course_id,
            c.name as course_name,
            c.credits,
            c.hours,
            s.name as semester_name,
            (
                SELECT COUNT(*)
                FROM Course_Selections cs
                WHERE cs.course_id = c.course_id AND cs.status = 1
            ) as student_count,
            c.max_students
        FROM Courses c
        JOIN Semesters s ON c.semester_id = s.semester_id
        WHERE c.teacher_id = %s
        ORDER BY s.start_date DESC, c.course_id
        """
        try:
            results = self.db.fetch_all(query, (teacher_id,))
            print(f"Debug - Teacher courses: {results}")  # 添加调试输出
            return results
        except Exception as e:
            print(f"Error in get_teacher_courses: {e}")
            return []