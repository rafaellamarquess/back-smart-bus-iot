from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime

class DataValidator(ABC):
    """Interface para validação de dados (Single Responsibility Principle)"""
    
    @abstractmethod
    async def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Valida os dados de entrada e retorna dados com flags de validação"""
        pass
    
    @abstractmethod
    def is_valid(self, data: Dict[str, Any]) -> bool:
        """Verifica se os dados são válidos"""
        pass

class DataTransformer(ABC):
    """Interface para transformação de dados (Single Responsibility Principle)"""
    
    @abstractmethod
    async def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transforma e enriquece os dados"""
        pass

class DataProcessor(ABC):
    """Interface principal para processamento de dados (Open/Closed Principle)"""
    
    @abstractmethod
    async def process(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Processa dados completos através do pipeline"""
        pass

class DataRepository(ABC):
    """Interface para persistência de dados (Dependency Inversion Principle)"""
    
    @abstractmethod
    async def save(self, data: Dict[str, Any]) -> str:
        """Salva dados e retorna ID"""
        pass
    
    @abstractmethod
    async def find_recent(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Busca dados recentes para análise de outliers"""
        pass

class AnalyticsService(ABC):
    """Interface para serviços de analytics (Interface Segregation Principle)"""
    
    @abstractmethod
    async def calculate_aggregates(self, timeframe: str = "1h") -> Dict[str, Any]:
        """Calcula métricas agregadas"""
        pass
    
    @abstractmethod
    async def detect_trends(self, days: int = 7) -> Dict[str, Any]:
        """Detecta tendências nos dados"""
        pass
    
    @abstractmethod
    async def get_data_quality_report(self) -> Dict[str, Any]:
        """Gera relatório de qualidade dos dados"""
        pass

class ETLPipeline(ABC):
    """Interface para pipeline ETL (Single Responsibility Principle)"""
    
    @abstractmethod
    async def extract(self, source_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extrai dados da fonte"""
        pass
    
    @abstractmethod
    async def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transforma dados"""
        pass
    
    @abstractmethod
    async def load(self, data: Dict[str, Any]) -> str:
        """Carrega dados no destino"""
        pass
    
    @abstractmethod
    async def execute(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Executa pipeline completo"""
        pass
