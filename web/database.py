import sqlite3
database = "investment.db"

def get_connection():
    conn = sqlite3.connect(database)
    conn.row_factory = sqlite3.Row
    return conn

def create_table():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""Create table if not exists users(id integer primary key autoincrement, username text not null,
      email text unique not null, password_hash text not null,created_at timestamp default current_timestamp )""")

    cursor.execute("""create table if not exists search_history(id integer primary key autoincrement, user_id integer not null, 
    principal real not null, years integer not null, penalty real not null, risk_strategy text not null,
     recommendation_count integer not null, searched_at timestamp default current_timestamp, foreign key(user_id) references users(id) )""")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_table()
    print("Table Created Successfully!")