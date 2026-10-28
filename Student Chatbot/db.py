import json
import os

import mysql.connector

from student import Student

SEED_FILE = os.path.join(os.path.dirname(__file__), "seed_students.json")


def _load_seed_students():
    with open(SEED_FILE, encoding="utf-8") as f:
        students = json.load(f)
    return [(s["name"], s["age"], s["grade"]) for s in students]

class Database:
    def __init__(self, host="localhost", user="root", password="", port=3306, database="student_db"):
        self.host = host
        self.user = user
        self.password = password
        self.port = port
        self.database = database

    def __connect(self, use_database=True):
        config = {
            "host": self.host,
            "user": self.user,
            "password": self.password,
            "port": self.port,
        }
        if use_database:
            config["database"] = self.database
        return mysql.connector.connect(**config)

    def create(self):
        conn = self.__connect(use_database=False)
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
        cursor.execute(f"USE {self.database}")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255),
                age INT,
                grade Decimal(3, 2)
            )
            """
        )
        cursor.execute("SELECT COUNT(*) FROM students")
        (count,) = cursor.fetchone()
        if count == 0:
            for student in _load_seed_students():
                cursor.execute(
                    f"INSERT INTO students (name, age, grade) VALUES {student}",
                )
            conn.commit()
        cursor.close()
        conn.close()

    def query_students(self, operator, value):
        if operator not in {"<", "<=", "=", ">=", ">"}:
            raise ValueError("Invalid comparison operator")
        conn = self.__connect()
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT name, grade FROM students "
            f"WHERE grade {operator} {value} "
            "ORDER BY grade DESC"
        )
        result = cursor.fetchall()
        cursor.close()
        conn.close()
        return result

    def insert_student(self, student):
        conn = self.__connect()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO students (name, age, grade) VALUES (%s, %s, %s)",
            (student.name, student.age, student.grade),
        )
        conn.commit()
        cursor.close()
        conn.close()

    def insert_students(self, students):
        conn = self.__connect()
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT INTO students (name, age, grade) VALUES (%s, %s, %s)",
            [(student.name, student.age, student.grade) for student in students],
        )
        conn.commit()
        cursor.close()
        conn.close()

    def fetch_students(self):
        conn = self.__connect()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, age, grade FROM students ORDER BY id")
        students = [Student(name, age, grade, student_id) for student_id, name, age, grade in cursor.fetchall()]

        cursor.close()
        conn.close()
        return students

    def update_student(self, student):
        conn = self.__connect()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE students SET name = %s, age = %s, grade = %s WHERE id = %s",
            (student.name, student.age, student.grade, student.id),
        )
        conn.commit()
        cursor.close()
        conn.close()

    def delete_student(self, student_id):
        conn = self.__connect()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM students WHERE id = %s",
            (student_id,)
        )
        conn.commit()
        cursor.close()
        conn.close()
