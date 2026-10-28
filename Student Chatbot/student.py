class Student:
    def __init__(self, name, age, grade, student_id):
        self.id = student_id
        self.name = name
        self.age = age
        self.grade = grade

    def update(self, name=None, age=None, grade=None):
        if name is not None:
            self.name = name
        if age is not None:
            self.age = age
        if grade is not None:
            self.grade = grade
