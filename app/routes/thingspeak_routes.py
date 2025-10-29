from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_db
from app.services.thingspeak_consumer_service import ThingSpeakConsumerService
import logging

router = APIRouter(prefix="/thingspeak", tags=["ThingSpeak Integration"])
logger = logging.getLogger(__name__)

_consumer_instance = None

@router.get("/save-data")
async def get_dados_thingspeak(
    results: int = Query(10, description="Número de registros para sincronizar", ge=1, le=100),
    db = Depends(get_db)
):
    """
    Busca e sincroniza dados do ThingSpeak para o MongoDB.
    
    Útil para:
    - Teste da integração
    - Recuperação de dados perdidos
    - Sincronização inicial
    """
    try:
        consumer = ThingSpeakConsumerService(db)
        result = await consumer.manual_sync(results)
        
        return {
            "sync_type": "manual",
            "requested_records": results,
            **result
        }
        
    except Exception as e:
        logger.error(f"Erro na sincronização manual do ThingSpeak: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/consumer/start")
async def start_thingspeak_consumer(
    interval: int = Query(60, description="Intervalo em segundos entre verificações", ge=30, le=3600),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db = Depends(get_db)
):
    """
    Inicia o consumer automático do ThingSpeak.
    
    O consumer rodará em background verificando novos dados periodicamente.
    """
    global _consumer_instance
    
    try:
        if _consumer_instance and _consumer_instance.is_running:
            return {
                "status": "already_running",
                "message": "ThingSpeak Consumer já está rodando",
                "interval": interval
            }
        
        _consumer_instance = ThingSpeakConsumerService(db)
        
        # Iniciar consumer em background
        background_tasks.add_task(_consumer_instance.start_consumer, interval)
        
        return {
            "status": "started",
            "message": f"ThingSpeak Consumer iniciado com intervalo de {interval}s",
            "interval": interval
        }
        
    except Exception as e:
        logger.error(f"Erro ao iniciar ThingSpeak Consumer: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/consumer/stop")
async def stop_thingspeak_consumer():
    """
    Para o consumer automático do ThingSpeak.
    """
    global _consumer_instance
    
    try:
        if not _consumer_instance or not _consumer_instance.is_running:
            return {
                "status": "not_running",
                "message": "ThingSpeak Consumer não está rodando"
            }
        
        _consumer_instance.stop_consumer()
        
        return {
            "status": "stopped",
            "message": "ThingSpeak Consumer parado com sucesso"
        }
        
    except Exception as e:
        logger.error(f"Erro ao parar ThingSpeak Consumer: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/consumer/status")
async def get_thingspeak_consumer_status():
    """
    Verifica o status do consumer do ThingSpeak.
    """
    global _consumer_instance
    
    is_running = _consumer_instance and _consumer_instance.is_running
    last_entry_id = _consumer_instance.last_entry_id if _consumer_instance else 0
    
    return {
        "consumer_running": is_running,
        "last_processed_entry_id": last_entry_id,
        "instance_exists": _consumer_instance is not None
    }

@router.get("/thingspeak")
async def test_thingspeak_connection(
    results: int = Query(5, description="Número de registros para testar", ge=1, le=20),
    db = Depends(get_db)
):
    """
    Testa a conexão com a API do ThingSpeak sem salvar dados.
    
    Útil para verificar:
    - Se as credenciais estão corretas
    - Se o canal está acessível  
    - Se há dados disponíveis
    """
    try:
        consumer = ThingSpeakConsumerService(db)
        data = await consumer.thingspeak_service.fetch_latest_data(results)

        if not data:
            return {
                "status": "no_data",
                "message": "Conexão OK, mas nenhum dado encontrado no canal",
                "records_found": 0
            }

        # Salvar cada registro no MongoDB via pipeline ETL
        processed_count = 0
        errors = []
        for item in data:
            try:
                etl_result = await consumer.etl_pipeline.execute(item)
                if etl_result['success']:
                    processed_count += 1
                else:
                    errors.append(f"ETL falhou para entry_id {item.get('entry_id')}: {etl_result.get('error')}")
            except Exception as e:
                errors.append(f"Erro ao processar entry_id {item.get('entry_id')}: {str(e)}")

        # Atualizar estado se processou dados
        if processed_count > 0 and data:
            max_entry_id = max(item.get("entry_id", 0) for item in data)
            await consumer.save_last_processed_entry_id(max_entry_id)

        return {
            "status": "success",
            "message": "Conexão com ThingSpeak funcionando e dados salvos no MongoDB",
            "records_found": len(data),
            "processed": processed_count,
            "errors": errors[:10],
            "sample_data": data,
            "latest_entry_id": max(item.get("entry_id", 0) for item in data) if data else 0
        }

    except Exception as e:
        logger.error(f"Erro ao testar conexão ThingSpeak: {e}")
        raise HTTPException(status_code=500, detail=str(e))
