from database import get_connection 
from werkzeug.security import generate_password_hash, check_password_hash

def create_user(username,email, password ):
    user = get_user_by_email(email)
    if user is not None:
        return False
    conn = get_connection()
    cursor = conn.cursor()
    password_hash = generate_password_hash(password)

    cursor.execute(""" insert into users(username, email, password_hash) values (?,?,?)""" , (username, email, password_hash))
    conn.commit()
    conn.close()
    return True

if __name__ == "__main__":
    create_user("aditya", "aditya@gmail.com", "testpass123")
    print("User Inserted Successfully")


def get_user_by_email(email):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(" select * from users where email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    return user

def verify_user(email, password):
    user = get_user_by_email(email)
    if user is None:
        return False
    if check_password_hash(user['password_hash'], password):
        return user
    return None
  