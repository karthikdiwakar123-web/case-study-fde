from fastapi import FastAPI
from database import init_db
import routers
from fastapi.middleware.cors import CORSMiddleware

import search_engine
app = FastAPI()


# Configure CORS origins
origins = [
    "http://localhost:4200", # Angular dev server
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the router into the main app instance
app.include_router(routers.router)

@app.get("/api")
def read_root():
    return {"message": "Welcome to the Support Ticket AI Tool"}

@app.on_event("startup")
def startup():
    init_db()
    search_engine.load_index()