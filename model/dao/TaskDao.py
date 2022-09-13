from typing import List

from pyrebase.pyrebase import Firebase

from domain.ObjectWrapper import ObjectMapper
from model.data.Task import Task


class TaskDao:

    def __init__(self, fb: Firebase):
        self.db = fb.database()

    def get_all(self) -> List[Task]:
        tasks = self.db.child("tasks").get()
        return ObjectMapper.parse_tasks(tasks) if tasks.each() is not None else []

    def increment_task_answered(self, task: Task):
        update_dict = {"answered": task.answered + 1}
        self.db.child("tasks").child(task.task_id).update(update_dict)

    def insert(self, task: Task):
        self.db.child("tasks").child(task.task_id).set(task.__dict__)
