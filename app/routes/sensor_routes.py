from fastapi import APIRouter, Depends, HTTPException, Header, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_db
from app.models.sensor import SensorReading, SensorReadingCreate
from app.services.sensor_service import SensorService
from app.processors.etl_pipeline import SensorETLPipeline, MongoDataRepository
import logging
from datetime import datetime

router = APIRouter(prefix="/sensors", tags=["Sensors"])
logger = logging.getLogger(__name__)

sensor_service = SensorService()

@router.post("/ingest")
async def ingest_data(
    reading: SensorReadingCreate,
    db: AsyncIOMotorDatabase = Depends(get_db), # type: ignore
    iot_api_key: str = Header(None)
):
    """
    Recebe dados do sensor ESP32, salva no MongoDB e envia ao ThingSpeak.
    Exige o cabeçalho com a chave IoT válida.
    """
    # Verificação da chave IoT
    from app.core.config import settings
    if iot_api_key != settings.iot_api_key:
        raise HTTPException(status_code=401, detail="Chave IoT inválida.")

    try:
        # Pipeline ETL para processamento avançado dos dados
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

        # Enviar para ThingSpeak
        await sensor_service.send_to_thingspeak(
            temperature=reading.temperature,
            humidity=reading.humidity
        )

        logger.info("✅ Dados enviados ao ThingSpeak com sucesso.")
        
        # Resposta enriquecida com informações do pipeline ETL
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
    

@router.get("/thingspeak")
async def get_thingspeak_data(
    results: int = Query(10, description="Número de registros para buscar", ge=1, le=50),
    db = Depends(get_db)
):
    """
    Busca dados do ThingSpeak APENAS se houver dados novos.
    Impede duplicatas e processamento desnecessário.
    """
    try:
        # 1. Buscar último entry_id já processado no banco
        latest_processed = await db.sensor_readings.find_one(
            {"source": "thingspeak"}, 
            sort=[("thingspeak_entry_id", -1)]
        )
        last_entry_id = latest_processed.get("thingspeak_entry_id", 0) if latest_processed else 0
        
        # 2. Buscar dados do ThingSpeak
        data = await sensor_service.fetch_thingspeak_data(results)
        
        # 3. Filtrar APENAS dados novos (entry_id maior que o último processado)
        new_data = [item for item in data if item.get("entry_id", 0) > last_entry_id]
        
        if new_data:
            # 4. Processar APENAS dados novos
            repository = MongoDataRepository(db)
            etl_pipeline = SensorETLPipeline(repository)
            processed_count = 0
            
            for item in new_data:
                try:
                    # Adicionar entry_id para controle de duplicatas
                    item["thingspeak_entry_id"] = item.get("entry_id")
                    etl_result = await etl_pipeline.execute(item)
                    if etl_result['success']:
                        processed_count += 1
                except Exception as e:
                    logger.error(f"Erro ETL entry_id {item.get('entry_id')}: {e}")

            return {
                "status": "success",
                "message": f"{processed_count} novos dados processados do ThingSpeak",
                "new_records": len(new_data),
                "last_processed_entry_id": max(item.get("entry_id", 0) for item in new_data),
                "data": new_data[:3]  # Amostra
            }
        else:
            # 5. NENHUM dado novo - retornar última leitura SEM processar
            latest = await db.sensor_readings.find_one({}, sort=[("recorded_at", -1)])
            if latest:
                latest["id"] = str(latest["_id"])
                del latest["_id"]
                return {
                    "status": "no_new_data",
                    "message": "Nenhum dado novo. Exibindo última leitura.",
                    "last_processed_entry_id": last_entry_id,
                    "latest_reading": latest
                }
            else:
                return {
                    "status": "no_data",
                    "message": "Nenhum dado encontrado no ThingSpeak ou banco.",
                    "records_found": 0
                }

    except Exception as e:
        logger.error(f"Erro ao buscar ThingSpeak: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    

@router.get("/readings")
async def get_sensor_readings(
    limit: int = Query(20, description="Número de leituras a retornar", ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_db) # type: ignore
):
    """
    Retorna as últimas leituras dos sensores armazenadas no MongoDB.
    """
    try:
        cursor = db.sensor_readings.find().sort("recorded_at", -1).limit(limit)
        readings = []
        async for doc in cursor:
            doc["id"] = str(doc["_id"])
            del doc["_id"]
            readings.append(doc)
        
        return {
            "readings": readings, 
            "count": len(readings),
            "limit": limit
        }
    
    except Exception as e:
        logger.error(f"❌ Erro ao buscar leituras: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/latest")
async def get_latest_reading(
    db: AsyncIOMotorDatabase = Depends(get_db) # type: ignore
):
    """
    Retorna a última leitura dos sensores.
    """
    try:
        latest = await db.sensor_readings.find_one({}, sort=[("recorded_at", -1)])
        
        if not latest:
            raise HTTPException(status_code=404, detail="Nenhuma leitura encontrada")
        
        latest["id"] = str(latest["_id"])
        del latest["_id"]
        
        return latest
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao buscar última leitura: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test")
async def test_sensor_data(
    temperature: float = Query(..., description="Temperatura de teste", ge=-40.0, le=80.0),
    humidity: float = Query(..., description="Umidade de teste", ge=0.0, le=100.0),
    db: AsyncIOMotorDatabase = Depends(get_db) # type: ignore
):
    """
    Endpoint para testar envio de dados para ThingSpeak.
    NÃO salva no MongoDB, apenas envia para ThingSpeak.
    """
    try:
        success = await sensor_service.send_to_thingspeak(temperature, humidity)
        
        if not success:
            raise HTTPException(status_code=400, detail="Falha ao enviar ao ThingSpeak.")
        
        return {
            "status": "success",
            "message": f"Dados de teste enviados ao ThingSpeak: {temperature}°C / {humidity}%",
            "data": {
                "temperature": temperature,
                "humidity": humidity,
                "device_id": "TEST_MANUAL"
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro no teste do ThingSpeak: {e}")
        raise HTTPException(status_code=500, detail=str(e))
