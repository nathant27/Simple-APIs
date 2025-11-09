from typing import Union

from fastapi import FastAPI
from pydantic import BaseModel
import random, time
import asyncio


app = FastAPI()

class Item(BaseModel):
    name: str
    price: float
    is_offer: Union[bool, None] = None

@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}

@app.put("/items/{item_id}")
def update_item(item_id: int, item: Item):
    return {"item_name": item.price, "item_id": item_id}

#Do not use time.sleep as it will block event loop in that worker
#If I make two separate calls, the second call needs to wait for the first call to finish
@app.get("/delay")
def blocking_delay():
    time.sleep(15)
    return random.randint(1,10)

@app.get("/nb-delay")
async def nonblocking_delay():
    await asyncio.sleep(10)
    return random.randint(5, 15)

# If you run nb-delay

# Order matters! Path operations are evaluated in the order they are defined
#So if you define a static path first, it will take precedence over a dynamic path
@app.get("/users/me")
def read_user_me():
    return {"user_id": "the current user"}

@app.get("/users/{user_id}")
def read_user(user_id: str):
    return {"user_id": user_id}
# Vise versa, would only match to the dynamic path, and not the static path

# Can not redine a path operation(same REST method and path)

from enum import Enum

class ModelName(str, Enum): # str is the type of the values
    cat = "cat"
    dog = "dog"
    rabbit = "rabbit"

@app.get("/models/{model_name}")
async def get_model(model_name: ModelName):
    if model_name == ModelName.cat:
        return {"model_name": model_name, "message": "Meow!"}
    if model_name == ModelName.dog:
        return {"model_name": model_name, "message": "Woof!"}
    if model_name == ModelName.rabbit:
        return {"model_name": model_name, "message": "Squeak!"}
    return {"model_name": model_name, "message": "Unknown model"}

@app.get("/path/{file_path:path}")
def read_file(file_path: str):
    return {"file_path": file_path}
