from typing import Dict, Any, List
from app.utils.cleaning import clean_reading
from app.crud.sensors import create_reading, get_latest_reading, get_history, get_total_readings
from app.core.database import get_db
from app.core.config import settings
import math
import httpx
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class SensorService:
    def __init__(self):
        self.collection_name = settings.mongodb_collection
        self.thingspeak_write_url = "http://api.thingspeak.com/update"
        self.thingspeak_read_url = "http://api.thingspeak.com/channels"
        self.thingspeak_write_api_key = settings.thingspeak_write_api_key
        self.thingspeak_read_api_key = settings.thingspeak_read_api_key
        self.thingspeak_channel_id = settings.thingspeak_channel_id

    async def process_and_store(self, raw_data: Dict[str, Any]) -> str:
        cleaned = clean_reading(
            raw_data.get("temperature"),
            raw_data.get("humidity")
        )
        heat_index = self._calculate_heat_index(cleaned["temperature"], cleaned["humidity"])
        doc = {
            **cleaned,
            "device_id": raw_data.get("device_id"),
            "heat_index": heat_index,
            "raw": raw_data
        }
        db = await anext(get_db())
        return await create_reading(db[self.collection_name], doc)

    async def get_latest(self) -> Dict[str, Any]:
        db = await anext(get_db())
        return await get_latest_reading(db[self.collection_name])

    async def get_history_data(self, limit: int = 100) -> Dict[str, Any]:
        db = await anext(get_db())
        readings = await get_history(db[self.collection_name], limit)
        total = await get_total_readings(db[self.collection_name])
        return {"readings": readings, "total": total}

    async def send_to_thingspeak(self, temperature: float, humidity: float) -> bool:
        """Envia dados para ThingSpeak"""
        try:
            params = {
                "api_key": self.thingspeak_write_api_key,
                "field1": temperature,
                "field2": humidity
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.thingspeak_write_url, params=params)
            success = response.status_code == 200
            if success:
                logger.info(f"✅ Thingspeak: T={temperature}°C H={humidity}%")
            else:
                logger.error(f"❌ Thingspeak: {response.status_code}")
            return success
        except Exception as e:
            logger.error(f"❌ Thingspeak Error: {e}")
            return False

    async def fetch_thingspeak_data(self, results: int = 10) -> List[Dict[str, Any]]:
        """Busca os dados mais recentes do canal ThingSpeak"""
        try:
            url = f"{self.thingspeak_read_url}/{self.thingspeak_channel_id}/feeds.json"
            params = {
                "api_key": self.thingspeak_read_api_key,
                "results": results
            }
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, params=params)
            if response.status_code != 200:
                logger.error(f"❌ ThingSpeak Read API: {response.status_code}")
                return []
            data = response.json()
            feeds = data.get("feeds", [])
            sensor_data = []
            for feed in feeds:
                try:
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

    def _calculate_heat_index(self, temp: float, hum: float) -> float:
        """NOAA Heat Index Formula"""
        if hum < 13 and temp >= 80:
            hi = (-42.379 + 2.04901523*temp + 10.14333127*hum -
                  0.22475541*temp*hum - 0.00683783*temp*temp -
                  0.05481717*hum*hum + 0.00122874*temp*temp*hum +
                  0.00085282*temp*hum*hum - 0.00000199*temp*temp*hum*hum)
            adjustment = ((13 - hum) / 4) * math.sqrt((17 - abs(temp - 95.)) / 17)
            hi += adjustment
        else:
            hi = temp
        return round(hi, 2)