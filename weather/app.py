from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from weather.core.accounts.storage import UPLOADS_DIRECTORY
from weather.routers import accounts, authenticate, weather

app = FastAPI()

origins = [
    'http://localhost:3000',  # React
    'http://localhost:4200',  # Angular
    "https://weatherui.duckdns.org",  # Servidor Oracle
    'http://127.0.0.1:5500',  # Live Server VSCode
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

UPLOADS_DIRECTORY.mkdir(parents=True, exist_ok=True)
app.mount('/uploads', StaticFiles(directory=UPLOADS_DIRECTORY), name='uploads')

app.include_router(
    router=accounts.router, prefix='/api/v1/accounts', tags=['accounts']
)
app.include_router(
    router=authenticate.router,
    prefix='/api/v1/authenticate',
    tags=['authenticate'],
)
app.include_router(
    router=weather.router,
    prefix='/api/v1/weather-city',
    tags=['weather'],
)


@app.get('/health_check', status_code=status.HTTP_200_OK)
def health_check():
    return {'status': 'ok'}
