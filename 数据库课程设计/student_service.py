from db_connection import DatabaseConnection


class StudentService:
    def __init__(self):
        self.db = DatabaseConnection()

    def query_available_courses(self, student_id):
        """获取可选课程列表"""
        query = """
        SELECT 
            c.course_id,
            c.name as course_name,
            t.name as teacher_name
        FROM Courses c
        JOIN Teachers t ON c.teacher_id = t.teacher_id
        WHERE c.course_id NOT IN (
            SELECT course_id 
            FROM Course_Selections 
            WHERE student_id = %s AND status = 1
        )
        AND c.max_students > (
            SELECT COUNT(*) 
            FROM Course_Selections 
            WHERE course_id = c.course_id AND status = 1
        )
        """
        courses = self.db.fetch_all(query, (student_id,))
        print("Debug - Available courses:", courses)

        result = [
            {
                'id': course[0],
                'text': f"{course[1]} ({course[2]})"
            }
            for course in courses
        ]
        print("Debug - Formatted result:", result)
        return result

    def select_course(self, student_id, course_id):
        try:
            print(f"Debug - Attempting to select course: student_id={student_id}, course_id={course_id}")

            # 首先验证学生ID是否存在
            check_student_query = """
            SELECT student_id FROM Students WHERE student_id = %s
            """
            student_exists = self.db.fetch_one(check_student_query, (student_id,))
            print(f"Debug - Student check result: {student_exists}")

            if not student_exists:
                print("Debug - Student not found")
                return False

            # 检查课程是否存在
            check_course_query = """
            SELECT course_id FROM Courses WHERE course_id = %s
            """
            course_exists = self.db.fetch_one(check_course_query, (course_id,))
            print(f"Debug - Course check result: {course_exists}")

            if not course_exists:
                print("Debug - Course not found")
                return False

            # 检查是否已选
            check_query = """
            SELECT selection_id FROM Course_Selections 
            WHERE student_id = %s AND course_id = %s AND status = 1
            """
            existing = self.db.fetch_one(check_query, (student_id, course_id))
            print(f"Debug - Existing selection check result: {existing}")

            if existing:
                print("Debug - Course already selected")
                return False

            # 检查课程容量
            capacity_query = """
            SELECT 
                c.max_students,
                COUNT(cs.selection_id) as current_students
            FROM Courses c
            LEFT JOIN Course_Selections cs ON c.course_id = cs.course_id 
                AND cs.status = 1
            WHERE c.course_id = %s
            GROUP BY c.course_id, c.max_students
            """
            capacity_result = self.db.fetch_one(capacity_query, (course_id,))
            print(f"Debug - Capacity check result: {capacity_result}")

            if not capacity_result:
                print("Debug - Course not found")
                return False

            max_students, current_students = capacity_result
            print(f"Debug - Max students: {max_students}, Current students: {current_students}")

            if current_students >= max_students:
                print("Debug - Course is full")
                return False

            # 选课
            insert_query = """
            INSERT INTO Course_Selections 
                (student_id, course_id, select_time, status)
            VALUES 
                (%s, %s, NOW(), 1)
            """
            success = self.db.execute_query(insert_query, (student_id, course_id))
            print(f"Debug - Insert result: {success}")

            return bool(success)

        except Exception as e:
            print(f"Debug - Error in select_course: {e}")
            return False

    def query_grades(self, student_id):
        query = """
        SELECT 
            c.name, 
            COALESCE(g.score, NULL) as score,
            COALESCE(g.grade_type, NULL) as grade_type
        FROM Course_Selections cs
        JOIN Courses c ON cs.course_id = c.course_id
        LEFT JOIN Grades g ON cs.selection_id = g.selection_id
        WHERE cs.student_id = %s AND cs.status = 1
        """
        return self.db.fetch_all(query, (student_id,))

    def drop_course(self, student_id, course_id):
        try:
            print(f"Debug - Attempting to drop course: student_id={student_id}, course_id={course_id}")

            # 首先检查选课记录是否存在
            check_selection_query = """
            SELECT cs.selection_id, g.grade_id
            FROM Course_Selections cs
            LEFT JOIN Grades g ON cs.selection_id = g.selection_id
            WHERE cs.student_id = %s 
            AND cs.course_id = %s 
            AND cs.status = 1
            """
            selection = self.db.fetch_one(check_selection_query, (student_id, course_id))
            print(f"Debug - Selection check result: {selection}")

            if not selection:
                print("Debug - No active selection found")
                return False

            selection_id, grade_id = selection

            # 检查是否已经有成绩
            if grade_id:
                print("Debug - Cannot drop course with grades")
                return False

            # 更新选课状态为退课
            update_query = """
            UPDATE Course_Selections 
            SET status = 0,
                select_time = NOW()  -- 记录退课时间
            WHERE selection_id = %s
            """
            success = self.db.execute_query(update_query, (selection_id,))
            print(f"Debug - Drop course result: {success}")

            return bool(success)

        except Exception as e:
            print(f"Debug - Error in drop_course: {e}")
            return False

    def get_selected_courses(self, student_id):
        """获取已选课程列表"""
        query = """
        SELECT 
            c.course_id,
            c.name as course_name,
            t.name as teacher_name,
            CASE WHEN g.grade_id IS NOT NULL THEN 1 ELSE 0 END as has_grade,
            cs.selection_id
        FROM Course_Selections cs
        JOIN Courses c ON cs.course_id = c.course_id
        JOIN Teachers t ON c.teacher_id = t.teacher_id
        LEFT JOIN Grades g ON cs.selection_id = g.selection_id
        WHERE cs.student_id = %s 
        AND cs.status = 1
        ORDER BY cs.select_time DESC
        """
        courses = self.db.fetch_all(query, (student_id,))
        print(f"Debug - Selected courses: {courses}")
        return courses

    def get_student_grades(self, student_id):
        """获取学生的成绩信息"""
        query = """
        SELECT 
            c.name, 
            COALESCE(g.score, NULL) as score,
            COALESCE(g.grade_type, NULL) as grade_type
        FROM Course_Selections cs
        JOIN Courses c ON cs.course_id = c.course_id
        LEFT JOIN Grades g ON cs.selection_id = g.selection_id
        WHERE cs.student_id = %s AND cs.status = 1
        """
        return self.db.fetch_all(query, (student_id,))