from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class itemRequestFormat(BaseModel):
    title: str
    description: str

idx = 0
list_items = {} #for testing

# user registration
#responds with token for authentication if successful


# user login 
#responds with token for authentication if successful

@app.post("/todos")
# create to do item
def create_item(item: itemRequestFormat):
    global idx
    list_items[idx] = {
        "idx": idx,
        "title": item.title,
        "description": item.description
    }
    idx += 1

    return 

@app.get("/todos")
def get_all_items():
    print(list_items)
    return list_items

# update to do item
@app.put("/todos/{item_id}")
def update_item(item_id: int, item: itemRequestFormat):
    if item_id in list_items:
        list_items[item_id].update({
            "title": item.title,
            "description": item.description
        })
        return list_items[item_id]
        
    return {"error": "Item not found"}

# delete to do item
