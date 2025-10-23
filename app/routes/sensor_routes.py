from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Dict
from app.services.thingspeak_service import ThingspeakService
from app.core.security import verify_iot_key
from app.core.database import get_db
from app.core.config import settings
from app.crud.sensors import create_reading, get_latest_reading, get_history

router = APIRouter(prefix="/sensors", tags=["Sensors"])
thingspeak_service = ThingspeakService()

class SensorData(BaseModel):
    temperature: float
    humidity: float
    device_id: str = "esp32-default"

@router.post("/ingest")
async def ingest_data(data: SensorData, db=Depends(get_db), _=Depends(verify_iot_key)):
    """Recebe dados do ESP32 e envia para Thingspeak"""
    inserted_id = await create_reading(db[settings.mongodb_collection], data.dict())
    await thingspeak_service.send_data(data.temperature, data.humidity)
    return {"status": "ok", "id": inserted_id}

@router.get("/latest")
async def latest(db=Depends(get_db)):
    return await get_latest_reading(db[settings.mongodb_collection])

@router.get("/history")
async def history(limit: int = 100, db=Depends(get_db)):
    return await get_history(db[settings.mongodb_collection], limit)
