from motor.motor_asyncio import AsyncIOMotorClient


class MongoMotorManager:

    def __init__(self) -> None:
        self.MONGO_DETAILS = "mongodb://mongo:mongo@localhost:27017"
        self.database = None
        self.client = None

    def startup(self, database: str) -> AsyncIOMotorClient:
        self.client = AsyncIOMotorClient(self.MONGO_DETAILS)
        self.database = self.client.get_database(database)
        return self.database


    def shutdown(self):
        self.client.close()


db = MongoMotorManager()
