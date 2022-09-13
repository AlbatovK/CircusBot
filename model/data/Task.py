class Task:

    def __init__(self, task_id: int, description: str, answer: str, answered: int):
        self.task_id = task_id
        self.description: str = description
        self.answer: str = answer
        self.answered: int = answered

    def __repr__(self):
        return str(self.task_id)
