# Student Database Management System with Chatbot

A Streamlit app for managing a MySQL student database, with admin and user logins and a simple chatbot that answers questions about student grades.

[Watch the demo video](https://drive.google.com/file/d/17uoF6C5zFMtNsLtseoYlCpxzx9QzMfrx/view?usp=sharing)

## Features

- **Login / Registration**: admins log in with the account in `credentials.json`; new users register and are saved to `users.json`. Passwords are stored as SHA-256 hashes.
- **Admin Dashboard**: view, add, update and delete students, bulk-import students from a CSV file, and use the chatbot.
- **User Dashboard**: ask the chatbot about student data.
- **Chatbot**: answers these predefined questions:
  - `List Student > 3.3`
  - `List Student < 2`
  - `List Student = 4`

## Requirements

- Python 3.10+
- MySQL server (installed directly, or through XAMPP) running on `localhost:3306`

## Setup

1. Start MySQL. The app connects as `root` with an empty password by default. To use other settings, change the defaults in `Database.__init__` in `db.py`.
2. Install the dependencies:

   ```bash
   python -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Run the app:

   ```bash
   streamlit run app.py
   ```

On first run, the app creates the `student_db` database and `students` table and fills it with the students in `seed_students.json`.

## Default accounts

| Role  | Username | Password   |
|-------|----------|------------|
| Admin | `admin`  | `admin123` |

To log in as a normal user, create an account on the **Register** tab first.

## CSV upload

In the admin dashboard, open **Upload CSV** and choose a UTF-8 CSV file with a header row of `name,age,grade`. Age must be a whole number from 1 to 120 and grade a number from 0 to 4. `sample_students.csv` is an example file.

## Project structure

```
app.py               Streamlit app (login, registration, dashboards, chat UI)
student.py           Student class
db.py                Database class (MySQL CRUD)
bot.py               Chatbot class
message.py           Chat message classes
credentials.json     Admin credentials (hashed password)
users.json           Registered users (hashed passwords)
seed_students.json   Students loaded into an empty database
sample_students.csv  Example file for the CSV upload
requirements.txt     Python dependencies
```

## Notes

- `grade` is stored as `DECIMAL(3,2)` instead of `VARCHAR(50)` so the chatbot can compare grades as numbers.
