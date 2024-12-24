from db_connection import DatabaseConnection


class AuthService:
    def __init__(self):
        self.db = DatabaseConnection()

    def login(self, username, password):
        try:
            query = """
            SELECT user_id, role, status 
            FROM Users 
            WHERE username = %s AND password = %s AND status = 1
            """
            result = self.db.fetch_one(query, (username, password))

            if result:
                return {
                    'user_id': result[0],
                    'role': result[1],
                    'status': result[2]
                }
            return None
        except Exception as e:
            print(f"Login error: {e}")
            return None

    def change_password(self, user_id, old_password, new_password):
        query = "SELECT user_id FROM Users WHERE user_id = %s AND password = %s"
        if not self.db.fetch_one(query, (user_id, old_password)):
            return False

        update_query = "UPDATE Users SET password = %s WHERE user_id = %s"
        self.db.execute_query(update_query, (new_password, user_id))
        return True