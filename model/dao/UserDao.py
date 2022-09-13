from pyrebase.pyrebase import Firebase

from domain.ObjectWrapper import ObjectMapper
from model.data.Task import Task
from model.data.User import User


class UserDao:

    def __init__(self, fb: Firebase):
        self.db = fb.database()

    def get_all(self):
        users = self.db.child("users").get()
        return ObjectMapper.parse_users(users) if users.each() is not None else []

    def get_done_tasks(self, usr: User):
        tasks = self.db.child("users").child(usr.login).child("done").get()
        return ObjectMapper.parse_tasks(tasks) if tasks.each() is not None else []

    def do_task(self, usr: User, task: Task):
        update_dict = {"score": usr.score}
        self.db.child("users").child(usr.login).update(update_dict)
        self.db.child("users").child(usr.login).child("done").child(task.task_id).set(task.__dict__)

    def insert(self, usr: User):
        user_dict = usr.__dict__
        self.db.child("users").child(usr.login).set(user_dict)
