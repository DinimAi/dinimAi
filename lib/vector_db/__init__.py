from abc import ABC, abstractmethod


class Database(ABC):

    def __init__(self):
        self.db = self.connect()

    @abstractmethod
    def connect(self):
        raise NotImplementedError("connect method not implemented")

    @abstractmethod
    def insert(self, item):
        raise NotImplementedError("insert method not implemented")

    @abstractmethod
    def query(self, query):
        raise NotImplementedError("query method not implemented")
