from pyrebase.pyrebase import Firebase

from domain.ObjectWrapper import ObjectMapper
from model.data.User import User


class UserDao:

    def __init__(self, fb: Firebase):
        self.db = fb.database()

    def get_all(self):
        users = self.db.child("users").get()
        return ObjectMapper.parse_users(users) if users.each() is not None else []

    def insert(self, usr: User):
        user_dict = usr.__dict__
        self.db.child("users").push(user_dict)
