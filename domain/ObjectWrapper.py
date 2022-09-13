from typing import List

from pyrebase.pyrebase import PyreResponse

from model.data.Task import Task
from model.data.User import User


class ObjectMapper:

    @staticmethod
    def parse_tasks(response: PyreResponse) -> List[Task]:
        def parse_single(item: PyreResponse) -> Task:
            val = item.val()
            task_id, description, answer, answered = val['task_id'], val['description'], val['answer'], val['answered']
            return Task(task_id, description, answer, answered)

        map_query = map(parse_single, response.each())
        return list(map_query)

    @staticmethod
    def parse_users(response: PyreResponse) -> List[User]:
        def parse_single(item: PyreResponse) -> User:
            val = item.val()
            user_id, score, name, login = val['user_id'], val['score'], val['name'], val['login']
            return User(user_id, score, name, login)

        map_query = map(parse_single, response.each())
        return list(map_query)
