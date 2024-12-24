def login(self, username, password):
    """用户登录验证"""
    try:
        print(f"Debug - Login attempt for username: {username}")  # 添加调试输出

        # 首先查询用户基本信息
        query = """
        SELECT 
            u.user_id,
            u.password,
            u.role,
            COALESCE(s.student_id, t.teacher_id, a.admin_id) as role_id
        FROM Users u
        LEFT JOIN Students s ON u.user_id = s.user_id
        LEFT JOIN Teachers t ON u.user_id = t.user_id
        LEFT JOIN Administrators a ON u.user_id = a.user_id
        WHERE u.username = %s
        """
        result = self.db.fetch_one(query, (username,))
        print(f"Debug - Query result: {result}")  # 添加调试输出

        if not result:
            print("Debug - User not found")
            return None

        user_id, stored_password, role, role_id = result

        # 验证密码
        if self.verify_password(password, stored_password):
            print(f"Debug - Login successful for {username}")
            return {
                'user_id': role_id,  # 使用角色ID
                'role': role
            }
        else:
            print(f"Debug - Password verification failed for {username}")
            return None

    except Exception as e:
        print(f"Error in login: {e}")
        return None


def verify_password(self, input_password, stored_password):
    """验证密码"""
    # 这里应该使用安全的密码哈希比较
    # 临时使用简单比较，实际应用中需要使用如 bcrypt 等安全方案
    return input_password == stored_password 