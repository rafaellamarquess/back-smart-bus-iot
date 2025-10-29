from fastapi import APIRouter, Depends, HTTPException, Header, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_db
from app.models.sensor import SensorReading, SensorReadingCreate
from app.services.thingspeak_service import ThingspeakService
from app.processors.etl_pipeline import SensorETLPipeline, MongoDataRepository
import logging
from datetime import datetime

router = APIRouter(prefix="/sensors", tags=["Sensors"])
logger = logging.getLogger(__name__)


thingspeak_service = ThingspeakService()



@router.post("/ingest")
async def ingest_data(
    reading: SensorReadingCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    iot_api_key: str = Header(None)
):
    """
    Recebe dados do sensor, salva no MongoDB e envia ao ThingSpeak.
    Exige o cabeçalho com a chave IoT válida.
    """
    # Verificação simples da chave IoT (substitua por uma função se quiser)
    from app.core.config import settings
    if iot_api_key != settings.iot_api_key:
        raise HTTPException(status_code=401, detail="Chave IoT inválida.")

    try:
        # 🆕 NOVO: Pipeline ETL para processamento avançado dos dados
        repository = MongoDataRepository(db)
        etl_pipeline = SensorETLPipeline(repository)
        
        # Executar pipeline ETL completo (validação, transformação, limpeza)
        etl_result = await etl_pipeline.execute(reading.dict())
        
        if not etl_result['success']:
            logger.error(f"❌ Falha no pipeline ETL: {etl_result.get('error')}")
            # Fallback: salvar dados básicos mesmo se ETL falhar
            sensor_data = reading.dict()
            sensor_data["recorded_at"] = datetime.utcnow()
            result = await db.sensor_readings.insert_one(sensor_data)
            document_id = str(result.inserted_id)
        else:
            document_id = etl_result['document_id']
            logger.info(f"✅ Pipeline ETL executado com sucesso. Score: {etl_result.get('data_quality_score', 0)}")

        # Continuar com ThingSpeak (funcionalidade original mantida)
        await thingspeak_service.send_data(
            temperature=reading.temperature,
            humidity=reading.humidity
        )

        logger.info("✅ Dados enviados ao ThingSpeak com sucesso.")
        
        # 🆕 NOVO: Resposta enriquecida com informações do pipeline ETL
        response = {
            "status": "ok", 
            "id": document_id,
            "etl_pipeline": {
                "executed": etl_result['success'],
                "data_quality_score": etl_result.get('data_quality_score', 0),
                "outliers_detected": etl_result.get('outliers_detected', {}),
                "processed_fields": etl_result.get('processed_fields', {})
            }
        }
        
        return response

    except Exception as e:
        logger.error(f"❌ Erro ao processar dados do sensor: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/test_thingspeak")
async def test_thingspeak(
    temperature: float = Query(25.0, description="Temperatura de teste"),
    humidity: float = Query(60.0, description="Umidade de teste")
):
    """
    Envia manualmente uma leitura ao ThingSpeak para teste.

    Exemplo:
    GET /api/sensors/test_thingspeak?temperature=25.6&humidity=80
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


@router.get("/readings")
async def get_sensor_readings(
    limit: int = Query(10, description="Número de leituras a retornar"),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Retorna as últimas leituras dos sensores.
    """
    try:
        cursor = db.sensor_readings.find().sort("recorded_at", -1).limit(limit)
        readings = []
        async for doc in cursor:
            doc["id"] = str(doc["_id"])
            del doc["_id"]
            readings.append(doc)
        
        return {"readings": readings, "count": len(readings)}
    
    except Exception as e:
        logger.error(f"❌ Erro ao buscar leituras: {e}")
        raise HTTPException(status_code=500, detail=str(e))
