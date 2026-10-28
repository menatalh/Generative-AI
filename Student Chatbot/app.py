from hashlib import sha256
import csv
import hmac
import io
import json
import os

import streamlit as st
import mysql.connector

from bot import Chatbot
from db import Database
from message import UsrMsg
from student import Student


BASE_DIR = os.path.dirname(__file__)
ADMIN_FILE = os.path.join(BASE_DIR, "credentials.json")
USERS_FILE = os.path.join(BASE_DIR, "users.json")
OPTIONS = ["List Student > 3.3", "List Student < 2", "List Student = 4"]   

class App:
    def __init__(self):
        st.set_page_config(page_title="Student Chatbot")

        if "authenticated" not in st.session_state:
            st.session_state.authenticated = False
        if "username" not in st.session_state:
            st.session_state.username = None
        if "role" not in st.session_state:
            st.session_state.role = None
        if "chat_history" not in st.session_state:  
            st.session_state.chat_history = []

    def __hash(self, password):
        return sha256(password.encode()).hexdigest()

    def __authenticate(self, username, password, role):
        hashed_password = self.__hash(password)
        if role == "Admin":
            with open(ADMIN_FILE, encoding="utf-8") as file:
                admin = json.load(file)["admin"]
            return username == admin["username"] and hmac.compare_digest(hashed_password, admin["password"])

        with open(USERS_FILE, encoding="utf-8") as file:
            users = json.load(file)
        return any(username == user["username"] and hmac.compare_digest(hashed_password, user["password"]) for user in users)

    def __register(self, username, password):
        with open(USERS_FILE, encoding="utf-8") as file:
            users = json.load(file)
        with open(ADMIN_FILE, encoding="utf-8") as file:
            admin = json.load(file)["admin"]
        if username == admin["username"] or any(username == user["username"] for user in users):
            return False
        users.append({"username": username, "password": self.__hash(password)})
        with open(USERS_FILE, "w", encoding="utf-8") as file:
            json.dump(users, file, indent=4)
        return True

    def render_auth(self):
        st.title("Student Database Management System")
        login_tab, register_tab = st.tabs(["Login", "Register"])
        with login_tab:
            self.render_login()
        with register_tab:
            self.render_register()

    def render_register(self):
        with st.form("register_form", clear_on_submit=True):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            confirm = st.text_input("Confirm Password", type="password")
            submitted = st.form_submit_button("Register", type="primary")

        if submitted:
            username = username.strip()
            if not username or not password:
                st.error("Username and password are required")
            elif password != confirm:
                st.error("Passwords do not match")
            elif self.__register(username, password):
                st.success("Account created. You can now log in as a User")
            else:
                st.error("Username already exists")

    def render_login(self):
        with st.form("login_form"):
            role = st.selectbox("Login as", ["Admin", "User"])
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", type="primary")

        if submitted:
            if self.__authenticate(username, password, role):
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.role = role
                st.rerun()
            else:
                st.error("Invalid username or password.")

    def render_logout(self):
        with st.sidebar:
            st.write(f"Signed in as **{st.session_state.username}**")
            if st.button("Log out"):
                st.session_state.authenticated = False
                st.session_state.username = None
                st.session_state.role = None
                st.session_state.chat_history = []
                st.rerun()

    def __get_database(self):
        try:
            database = Database()
            database.create()
            return database
        except mysql.connector.Error:
            st.warning("Can't connect to the student database. Make sure MySQL is running.")
            return None

    def __student_form(self, key, submit_label, student=None):
        is_new = student is None
        if is_new:
            student = Student("", 18, 0.0, None)

        with st.form(key, clear_on_submit=is_new):
            name = st.text_input("Name", value=student.name)
            age = st.number_input("Age", min_value=1, max_value=120, value=student.age, step=1)
            grade = st.number_input("Grade", min_value=0.0, max_value=4.0, value=float(student.grade), step=0.01, format="%.2f")
            submitted = st.form_submit_button(submit_label, type="primary")

        if not submitted:
            return None
        name = name.strip()
        if not name:
            st.error("Name is required")
            return None
        student.update(name=name, age=int(age), grade=round(grade, 2))
        return student

    def __parse_csv(self, file):
        reader = csv.DictReader(io.StringIO(file.getvalue().decode("utf-8-sig")))
        columns = {"name", "age", "grade"}
        if reader.fieldnames is None or not columns.issubset(name.strip().lower() for name in reader.fieldnames):
            raise ValueError("CSV must have the columns: name, age, grade")

        students = []
        for line, row in enumerate(reader, start=2):
            row = {key.strip().lower(): (value or "").strip() for key, value in row.items() if key}
            try:
                name = row["name"]
                age = int(row["age"])
                grade = round(float(row["grade"]), 2)
            except ValueError:
                raise ValueError(f"Row {line}: age must be a whole number and grade a number")
            if not name:
                raise ValueError(f"Row {line}: name is required")
            if not 1 <= age <= 120:
                raise ValueError(f"Row {line}: age must be between 1 and 120")
            if not 0 <= grade <= 4:
                raise ValueError(f"Row {line}: grade must be between 0 and 4")
            students.append(Student(name, age, grade, None))

        if not students:
            raise ValueError("CSV has no students")
        return students

    def __select_student(self, students, key):
        return st.selectbox("Student", students, format_func=lambda student: f"#{student.id} {student.name}", key=key)

    def __succeed(self, message):
        st.session_state.flash = message
        st.rerun()

    def render_admin_dashboard(self):
        st.title("Admin Dashboard")
        flash = st.empty()
        if "flash" in st.session_state:
            flash.success(st.session_state.pop("flash"))
        database = self.__get_database()
        if database is None:
            return

        try:
            students = database.fetch_students()
        except mysql.connector.Error:
            st.error("Could not load students. Please try again.")
            return

        view_tab, add_tab, upload_tab, update_tab, delete_tab, chat_tab = st.tabs(
            ["View", "Add", "Upload CSV", "Update", "Delete", "Chatbot"]
        )

        with view_tab:
            if students:
                st.dataframe(
                    [{"ID": s.id, "Name": s.name, "Age": s.age, "Grade": float(s.grade)} for s in students],
                    hide_index=True
                )
            else:
                st.info("No students yet")

        with add_tab:
            student = self.__student_form("add_form", "Add student")
            if student:
                try:
                    database.insert_student(student)
                    self.__succeed(f"Added {student.name}")
                except mysql.connector.Error:
                    st.error("Database error. Please try again.")

        with upload_tab:
            st.write("Upload a CSV file with the columns **name**, **age** and **grade**.")
            file = st.file_uploader("CSV file", type="csv", key=f"csv_upload_{st.session_state.get('imports', 0)}")
            if file:
                try:
                    new_students = self.__parse_csv(file)
                except ValueError as error:
                    st.error(str(error))
                except UnicodeDecodeError:
                    st.error("CSV file must be UTF-8 encoded")
                else:
                    st.dataframe(
                        [{"Name": s.name, "Age": s.age, "Grade": s.grade} for s in new_students],
                        hide_index=True
                    )
                    if st.button(f"Import {len(new_students)} students", type="primary"):
                        try:
                            database.insert_students(new_students)
                            st.session_state.imports = st.session_state.get("imports", 0) + 1
                            self.__succeed(f"Imported {len(new_students)} students")
                        except mysql.connector.Error:
                            st.error("Database error. Please try again.")

        with update_tab:
            if not students:
                st.info("No students to update.")
            else:
                selected = self.__select_student(students, "update_student")
                student = self.__student_form(f"update_form_{selected.id}", "Save changes", selected)
                if student:
                    try:
                        database.update_student(student)
                        self.__succeed(f"Updated {student.name}")
                    except mysql.connector.Error:
                        st.error("Database error. Please try again")
                
        with delete_tab:
            if not students:
                st.info("No students to delete.")
            else:
                student = self.__select_student(students, "delete_student")
                if st.button("Delete student", type="primary"):
                    try:
                        database.delete_student(student.id)
                        self.__succeed(f"Deleted {student.name}")
                    except mysql.connector.Error:
                        st.error("Database error. Please try again.")

        with chat_tab:
            self.__render_chat(Chatbot(database))

    def render_user_dashboard(self):
        st.title("User Dashboard")
        database = self.__get_database()
        if database is None:
            return

        self.__render_chat(Chatbot(database))

    def __render_chat(self, chatbot):
        history = st.container()

        columns = st.columns(len(OPTIONS))
        for column, option in zip(columns, OPTIONS):
            if column.button(option, width="stretch"):
                self.__send(chatbot, option)

        prompt = st.chat_input("Ask about student data...")
        if prompt:
            self.__send(chatbot, prompt)

        with history:
            for message in st.session_state.chat_history:
                role = "user" if message.align == "right" else "assistant"
                with st.chat_message(role):
                    st.write(message.content)

    def __send(self, chatbot, prompt):
        st.session_state.chat_history.append(UsrMsg(prompt))
        st.session_state.chat_history.append(chatbot.respond(prompt))

    def run(self):
        if not st.session_state.authenticated:
            self.render_auth()
            return

        self.render_logout()
        if st.session_state.role == "Admin":
            self.render_admin_dashboard()
        else:
            self.render_user_dashboard()

if __name__ == "__main__":
    app = App()
    app.run()