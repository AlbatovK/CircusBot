class User:

    def __init__(self, user_id: int, score: int, name: str, login: str):
        self.user_id = user_id
        self.score = score
        self.name = name
        self.login = login

    def __repr__(self):
        return self.login
