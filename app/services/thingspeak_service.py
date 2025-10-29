import httpx
from app.core.config import settings
import logging
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class ThingspeakService:
    def __init__(self):
        self.write_url = "http://api.thingspeak.com/update"
        self.read_url = "http://api.thingspeak.com/channels"
        self.write_api_key = settings.thingspeak_write_api_key
        self.read_api_key = settings.thingspeak_read_api_key
        self.channel_id = settings.thingspeak_channel_id
    
    async def send_data(self, temperature: float, humidity: float) -> bool:
        """Envia dados para Thingspeak"""
        try:
            params = {
                "api_key": self.write_api_key,
                "field1": temperature,
                "field2": humidity
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.write_url, params=params)
                
            success = response.status_code == 200
            if success:
                logger.info(f"✅ Thingspeak: T={temperature}°C H={humidity}%")
            else:
                logger.error(f"❌ Thingspeak: {response.status_code}")
                
            return success
            
        except Exception as e:
            logger.error(f"❌ Thingspeak Error: {e}")
            return False

    async def fetch_latest_data(self, results: int = 10) -> List[Dict[str, Any]]:
        """
        Busca os dados mais recentes do canal ThingSpeak
        
        Args:
            results: Número de registros para buscar (máximo 8000)
        
        Returns:
            Lista de dados do canal com temperatura e umidade
        """
        try:
            url = f"{self.read_url}/{self.channel_id}/feeds.json"
            params = {
                "api_key": self.read_api_key,
                "results": results
            }
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, params=params)
                
            if response.status_code != 200:
                logger.error(f"❌ ThingSpeak Read API: {response.status_code}")
                return []
                
            data = response.json()
            feeds = data.get("feeds", [])
            
            # Converter dados do ThingSpeak para formato do backend
            sensor_data = []
            for feed in feeds:
                try:
                    # ThingSpeak retorna field1=temperature, field2=humidity
                    temp = feed.get("field1")
                    humidity = feed.get("field2")
                    created_at = feed.get("created_at")
                    
                    if temp and humidity and created_at:
                        sensor_data.append({
                            "temperature": float(temp),
                            "humidity": float(humidity),
                            "device_id": "ESP32_THINGSPEAK",
                            "thingspeak_created_at": created_at,
                            "entry_id": feed.get("entry_id")
                        })
                        
                except (ValueError, TypeError) as e:
                    logger.warning(f"⚠️ Dados inválidos do ThingSpeak: {feed} - {e}")
                    continue
            
            logger.info(f"📥 ThingSpeak: {len(sensor_data)} registros válidos de {len(feeds)} feeds")
            return sensor_data
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar dados do ThingSpeak: {e}")
            return []

    async def fetch_data_since_entry(self, last_entry_id: int = 0) -> List[Dict[str, Any]]:
        """
        Busca dados do ThingSpeak desde um entry_id específico (para evitar duplicatas)
        
        Args:
            last_entry_id: ID da última entrada processada
        
        Returns:
            Lista de novos dados desde o last_entry_id
        """
        try:
            # Buscar mais dados para garantir que peguemos as novidades
            all_data = await self.fetch_latest_data(results=100)
            
            # Filtrar apenas dados novos (entry_id > last_entry_id)
            new_data = [
                entry for entry in all_data 
                if entry.get("entry_id", 0) > last_entry_id
            ]
            
            if new_data:
                logger.info(f"🆕 {len(new_data)} novos registros desde entry_id {last_entry_id}")
            
            return new_data
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar novos dados do ThingSpeak: {e}")
            return []