from fastapi import APIRouter, Depends, HTTPException, Header, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_db
from app.models.sensor import SensorReading
from app.services.thingspeak_service import ThingspeakService
import logging

router = APIRouter(prefix="/api/v1/sensors", tags=["Sensors"])
logger = logging.getLogger(__name__)


thingspeak_service = ThingspeakService()



@router.post("/ingest")
async def ingest_data(
    reading: SensorReading,
    db: AsyncIOMotorDatabase = Depends(get_db),
    x_api_key: str = Header(None)
):
    """
    Recebe dados do sensor, salva no MongoDB e envia ao ThingSpeak.
    Exige o cabeçalho: X-API-Key
    """
    # Verificação simples da chave IoT (substitua por uma função se quiser)
    from app.core.config import settings
    if x_api_key != settings.iot_api_key:
        raise HTTPException(status_code=401, detail="Chave IoT inválida.")

    try:
        # Salva leitura no MongoDB
        result = await db.sensor_readings.insert_one(reading.dict())
        logger.info(f"📥 Sensor data saved: {result.inserted_id}")

        # Envia dados ao ThingSpeak
        await thingspeak_service.send_data(
            temperature=reading.temperature,
            humidity=reading.humidity
        )

        logger.info("✅ Dados enviados ao ThingSpeak com sucesso.")
        return {"status": "ok", "id": str(result.inserted_id)}

    except Exception as e:
        logger.error(f"❌ Erro ao processar dados do sensor: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/test_thingspeak")
async def test_thingspeak(
    temperature: float = Query(..., description="Temperatura de teste"),
    humidity: float = Query(..., description="Umidade de teste")
):
    """
    Envia manualmente uma leitura ao ThingSpeak para teste.

    Exemplo:
    GET /api/v1/sensors/test_thingspeak?temperature=25.6&humidity=80
    """
    try:
        success = await thingspeak_service.send_data(temperature, humidity)
        if success:
            return {
                "status": "success",
                "message": f"Dados enviados ao ThingSpeak: {temperature}°C / {humidity}%",
            }
        else:
            raise HTTPException(status_code=400, detail="Falha ao enviar ao ThingSpeak.")

    except Exception as e:
        logger.error(f"❌ Erro no teste do ThingSpeak: {e}")
        raise HTTPException(status_code=500, detail=str(e))
