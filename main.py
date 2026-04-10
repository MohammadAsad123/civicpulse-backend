from fastapi import FastAPI
from app.routes import complaints
from app.routes import dashboard
from app.routes import uploads
from app.routes import classification
from apscheduler.schedulers.background import BackgroundScheduler
from app.services.sla_monitor import check_sla_breaches
from fastapi.security import HTTPBearer
from fastapi import Security
from app.routes import inspectors
from app.routes import work_orders
from app.routes import notifications
from fastapi.middleware.cors import CORSMiddleware
from app.routes import whatsapp

app = FastAPI()
origins = [
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()


app.include_router(complaints.router)
app.include_router(dashboard.router)
app.include_router(uploads.router)
app.include_router(classification.router)
app.include_router(inspectors.router)
app.include_router(work_orders.router)
app.include_router(notifications.router)
app.include_router(whatsapp.router)

scheduler = BackgroundScheduler()
scheduler.add_job(check_sla_breaches, "interval", minutes=60)
scheduler.start()