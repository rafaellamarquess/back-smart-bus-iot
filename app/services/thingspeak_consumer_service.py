import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.services.thingspeak_service import ThingspeakService
from app.processors.etl_pipeline import SensorETLPipeline, MongoDataRepository
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

class ThingSpeakConsumerService:
    """
    Serviço que consome dados do ThingSpeak periodicamente e armazena no MongoDB
    """
    
    def __init__(self, db):
        self.db = db
        self.thingspeak_service = ThingspeakService()
        self.repository = MongoDataRepository(db)
        self.etl_pipeline = SensorETLPipeline(self.repository)
        self.consumer_collection = db.thingspeak_consumer_state
        self.is_running = False
        self.last_entry_id = 0
    
    async def get_last_processed_entry_id(self) -> int:
        """Recupera o último entry_id processado do MongoDB"""
        try:
            state = await self.consumer_collection.find_one({"_id": "consumer_state"})
            if state:
                return state.get("last_entry_id", 0)
            return 0
        except Exception as e:
            logger.error(f"❌ Erro ao recuperar estado do consumer: {e}")
            return 0
    
    async def save_last_processed_entry_id(self, entry_id: int):
        """Salva o último entry_id processado"""
        try:
            await self.consumer_collection.update_one(
                {"_id": "consumer_state"},
                {
                    "$set": {
                        "last_entry_id": entry_id,
                        "updated_at": datetime.utcnow()
                    }
                },
                upsert=True
            )
        except Exception as e:
            logger.error(f"❌ Erro ao salvar estado do consumer: {e}")
    
    async def process_new_data(self) -> int:
        """
        Processa novos dados do ThingSpeak e armazena no MongoDB
        
        Returns:
            Número de registros processados
        """
        try:
            # Recuperar último entry_id processado
            self.last_entry_id = await self.get_last_processed_entry_id()
            
            # Buscar novos dados do ThingSpeak
            new_data = await self.thingspeak_service.fetch_data_since_entry(self.last_entry_id)
            
            if not new_data:
                logger.debug(f"📊 Nenhum dado novo no ThingSpeak (último entry_id: {self.last_entry_id})")
                return 0
            
            processed_count = 0
            highest_entry_id = self.last_entry_id
            
            # Processar cada novo registro através do pipeline ETL
            for data in new_data:
                try:
                    # Executar pipeline ETL completo
                    etl_result = await self.etl_pipeline.execute(data)
                    
                    if etl_result['success']:
                        processed_count += 1
                        entry_id = data.get("entry_id", 0)
                        if entry_id > highest_entry_id:
                            highest_entry_id = entry_id
                        
                        logger.info(f"✅ ThingSpeak → MongoDB: T={data['temperature']}°C H={data['humidity']}% (entry_id: {entry_id})")
                    else:
                        logger.warning(f"⚠️ Falha no ETL para dados do ThingSpeak: {etl_result.get('error')}")
                        
                except Exception as e:
                    logger.error(f"❌ Erro ao processar registro do ThingSpeak: {data} - {e}")
                    continue
            
            # Atualizar último entry_id processado
            if highest_entry_id > self.last_entry_id:
                await self.save_last_processed_entry_id(highest_entry_id)
                self.last_entry_id = highest_entry_id
            
            if processed_count > 0:
                logger.info(f"🎯 ThingSpeak Consumer: {processed_count} registros processados com sucesso")
            
            return processed_count
            
        except Exception as e:
            logger.error(f"❌ Erro no processamento dos dados do ThingSpeak: {e}")
            return 0
    
    async def start_consumer(self, interval: int = 60):
        """
        Inicia o consumer em loop contínuo
        
        Args:
            interval: Intervalo em segundos entre verificações (padrão: 60s)
        """
        if self.is_running:
            logger.warning("⚠️ ThingSpeak Consumer já está rodando")
            return
        
        self.is_running = True
        logger.info(f"🚀 ThingSpeak Consumer iniciado (intervalo: {interval}s)")
        
        try:
            while self.is_running:
                try:
                    processed = await self.process_new_data()
                    
                    if processed > 0:
                        logger.info(f"📊 Ciclo completo: {processed} registros do ThingSpeak processados")
                    
                    # Aguardar próximo ciclo
                    await asyncio.sleep(interval)
                    
                except Exception as e:
                    logger.error(f"❌ Erro no ciclo do ThingSpeak Consumer: {e}")
                    await asyncio.sleep(interval)  # Continuar mesmo com erro
                    
        except asyncio.CancelledError:
            logger.info("🛑 ThingSpeak Consumer cancelado")
        finally:
            self.is_running = False
            logger.info("🔚 ThingSpeak Consumer finalizado")
    
    def stop_consumer(self):
        """Para o consumer"""
        self.is_running = False
        logger.info("🛑 Solicitação de parada do ThingSpeak Consumer")
    
    async def manual_sync(self, results: int = 10) -> dict:
        """
        Sincronização manual para testes ou recuperação de dados
        
        Args:
            results: Número de registros para buscar do ThingSpeak
        
        Returns:
            Relatório da sincronização
        """
        try:
            logger.info(f"🔄 Sincronização manual iniciada (últimos {results} registros)")
            
            # Buscar dados mais recentes do ThingSpeak
            data = await self.thingspeak_service.fetch_latest_data(results)
            
            if not data:
                return {
                    "status": "no_data",
                    "message": "Nenhum dado encontrado no ThingSpeak",
                    "processed": 0
                }
            
            processed_count = 0
            errors = []
            
            # Processar todos os dados
            for item in data:
                try:
                    etl_result = await self.etl_pipeline.execute(item)
                    if etl_result['success']:
                        processed_count += 1
                    else:
                        errors.append(f"ETL falhou para entry_id {item.get('entry_id')}: {etl_result.get('error')}")
                except Exception as e:
                    errors.append(f"Erro ao processar entry_id {item.get('entry_id')}: {str(e)}")
            
            # Atualizar estado se processou dados
            if processed_count > 0 and data:
                max_entry_id = max(item.get("entry_id", 0) for item in data)
                await self.save_last_processed_entry_id(max_entry_id)
            
            return {
                "status": "success",
                "message": f"Sincronização manual concluída",
                "total_fetched": len(data),
                "processed": processed_count,
                "errors": errors[:10],  # Limitar erros na resposta
                "error_count": len(errors)
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na sincronização manual: {e}")
            return {
                "status": "error",
                "message": f"Erro na sincronização: {str(e)}",
                "processed": 0
            }
