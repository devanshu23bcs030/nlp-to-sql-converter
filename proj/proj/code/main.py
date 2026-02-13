from fastapi import FastAPI
from routes import process
from routes import uploaddb
from fastapi.middleware.cors import CORSMiddleware

uploadrouter = uploaddb.router
getrouter = process.router
app = FastAPI()

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(uploadrouter)
app.include_router(getrouter)