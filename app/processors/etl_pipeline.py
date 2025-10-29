from typing import Dict, Any, List
from datetime import datetime
import logging
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.interfaces.data_interfaces import ETLPipeline, DataRepository
from app.processors.sensor_processor import SensorDataValidator, SensorDataTransformer, OutlierDetector

logger = logging.getLogger(__name__)

class MongoDataRepository(DataRepository):
    """Implementação concreta do repositório para MongoDB"""
    
    def __init__(self, db):
        self.db = db
        self.collection = db.sensor_readings
    
    async def save(self, data: Dict[str, Any]) -> str:
        """Salva dados no MongoDB e retorna ID"""
        result = await self.collection.insert_one(data)
        return str(result.inserted_id)
    
    async def find_recent(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Busca dados recentes para análise de outliers"""
        cursor = self.collection.find().sort("recorded_at", -1).limit(limit)
        recent_data = []
        async for doc in cursor:
            doc["id"] = str(doc["_id"])
            del doc["_id"]
            recent_data.append(doc)
        return recent_data

class SensorETLPipeline(ETLPipeline):
    """Pipeline ETL específico para dados de sensores IoT"""
    
    # Estatísticas globais do pipeline ETL
    GLOBAL_STATS = {
        'processed': 0,
        'valid': 0,
        'invalid': 0,
        'outliers': 0
    }

    def __init__(self, repository: DataRepository):
        self.repository = repository
        self.validator = SensorDataValidator()
        self.transformer = SensorDataTransformer()
        self.stats = SensorETLPipeline.GLOBAL_STATS
    
    async def extract(self, source_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extrai e prepara dados da fonte (sensor IoT)"""
        extracted_data = source_data.copy()
        
        # Adicionar metadados de extração
        extracted_data['extracted_at'] = datetime.utcnow()
        extracted_data['source'] = 'iot_sensor'
        
        # Log do processo de extração
        logger.info(f"📥 Dados extraídos do sensor: {extracted_data.get('device_id', 'unknown')}")
        
        return extracted_data
    
    async def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transforma dados através do pipeline de validação e enriquecimento"""
        # 1. Validação
        validated_data = await self.validator.validate(data)
        
        # 2. Detecção de outliers
        recent_data = await self.repository.find_recent(limit=50)
        outlier_detector = OutlierDetector(recent_data)
        
        if 'temperature' in validated_data:
            is_temp_outlier = outlier_detector.detect_temperature_outliers(validated_data['temperature'])
            validated_data['is_temperature_outlier'] = is_temp_outlier
            if is_temp_outlier:
                self.stats['outliers'] += 1
                logger.warning(f"🚨 Outlier de temperatura detectado: {validated_data['temperature']}°C")
        
        if 'humidity' in validated_data:
            is_humidity_outlier = outlier_detector.detect_humidity_outliers(validated_data['humidity'])
            validated_data['is_humidity_outlier'] = is_humidity_outlier
            if is_humidity_outlier:
                self.stats['outliers'] += 1
                logger.warning(f"🚨 Outlier de umidade detectado: {validated_data['humidity']}%")
        
        # 3. Transformação e enriquecimento
        if self.validator.is_valid(validated_data):
            transformed_data = await self.transformer.transform(validated_data)
            self.stats['valid'] += 1
            logger.info("✅ Dados válidos transformados com sucesso")
        else:
            transformed_data = validated_data
            self.stats['invalid'] += 1
            logger.warning(f"⚠️ Dados inválidos: {validated_data['validation']['errors']}")
        
        return transformed_data
    
    async def load(self, data: Dict[str, Any]) -> str:
        """Carrega dados transformados no MongoDB"""
        # Adicionar timestamp final de carregamento
        data['loaded_at'] = datetime.utcnow()
        
        # Salvar no repositório
        document_id = await self.repository.save(data)
        
        logger.info(f"💾 Dados salvos no MongoDB com ID: {document_id}")
        return document_id
    
    async def execute(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Executa pipeline ETL completo"""
        try:
            self.stats['processed'] += 1
            
            # Extract
            extracted_data = await self.extract(raw_data)
            
            # Transform
            transformed_data = await self.transform(extracted_data)
            
            # Load
            document_id = await self.load(transformed_data)
            
            # Resultado final
            result = {
                'success': True,
                'document_id': document_id,
                'data_quality_score': transformed_data.get('data_quality_score', 0),
                'is_valid': transformed_data.get('validation', {}).get('is_valid', False),
                'outliers_detected': {
                    'temperature': transformed_data.get('is_temperature_outlier', False),
                    'humidity': transformed_data.get('is_humidity_outlier', False)
                },
                'processed_fields': {
                    'heat_index': 'heat_index' in transformed_data,
                    'dew_point': 'dew_point' in transformed_data,
                    'comfort_level': 'comfort_level' in transformed_data
                }
            }
            
            logger.info(f"🎯 Pipeline ETL executado com sucesso. Score: {result['data_quality_score']}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Erro no pipeline ETL: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'document_id': None
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas globais do pipeline"""
        stats = SensorETLPipeline.GLOBAL_STATS
        return {
            **stats,
            'success_rate': (stats['valid'] / stats['processed'] * 100) if stats['processed'] > 0 else 0,
            'outlier_rate': (stats['outliers'] / stats['processed'] * 100) if stats['processed'] > 0 else 0
        }
