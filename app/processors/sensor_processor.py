import math
import statistics
from typing import Dict, Any, List
from datetime import datetime
from app.interfaces.data_interfaces import DataValidator, DataTransformer

class SensorDataValidator(DataValidator):
    """Validador específico para dados de sensores IoT"""
    
    def __init__(self):
        # Limites aceitáveis para os sensores
        self.temp_min = -40.0
        self.temp_max = 80.0
        self.humidity_min = 0.0
        self.humidity_max = 100.0
    
    async def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Valida dados e adiciona flags de qualidade"""
        validated_data = data.copy()
        
        # Flags de validação
        validated_data['validation'] = {
            'is_valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Validar temperatura
        if 'temperature' not in data:
            validated_data['validation']['errors'].append('temperature_missing')
            validated_data['validation']['is_valid'] = False
        else:
            temp = data['temperature']
            if not isinstance(temp, (int, float)):
                validated_data['validation']['errors'].append('temperature_invalid_type')
                validated_data['validation']['is_valid'] = False
            elif temp < self.temp_min or temp > self.temp_max:
                validated_data['validation']['errors'].append('temperature_out_of_range')
                validated_data['validation']['is_valid'] = False
            elif temp < -10 or temp > 50:  # Warning para temperaturas extremas mas possíveis
                validated_data['validation']['warnings'].append('temperature_extreme')
        
        # Validar umidade
        if 'humidity' not in data:
            validated_data['validation']['errors'].append('humidity_missing')
            validated_data['validation']['is_valid'] = False
        else:
            humidity = data['humidity']
            if not isinstance(humidity, (int, float)):
                validated_data['validation']['errors'].append('humidity_invalid_type')
                validated_data['validation']['is_valid'] = False
            elif humidity < self.humidity_min or humidity > self.humidity_max:
                validated_data['validation']['errors'].append('humidity_out_of_range')
                validated_data['validation']['is_valid'] = False
            elif humidity > 95:  # Warning para umidade muito alta
                validated_data['validation']['warnings'].append('humidity_very_high')
        
        return validated_data
    
    def is_valid(self, data: Dict[str, Any]) -> bool:
        """Verifica se os dados são válidos"""
        if 'validation' in data:
            return data['validation']['is_valid']
        return False

class SensorDataTransformer(DataTransformer):
    """Transformador específico para dados de sensores IoT"""
    
    async def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transforma e enriquece dados do sensor"""
        transformed_data = data.copy()
        
        # Adicionar timestamp de processamento
        transformed_data['processed_at'] = datetime.utcnow()
        
        # Calcular heat index se temperatura e umidade estão disponíveis
        if 'temperature' in data and 'humidity' in data:
            temp_c = data['temperature']
            humidity = data['humidity']
            
            # Converter para Fahrenheit para cálculo do heat index
            temp_f = (temp_c * 9/5) + 32
            heat_index_f = self._calculate_heat_index(temp_f, humidity)
            
            # Converter de volta para Celsius
            transformed_data['heat_index'] = (heat_index_f - 32) * 5/9
            
            # Calcular ponto de orvalho
            transformed_data['dew_point'] = self._calculate_dew_point(temp_c, humidity)
            
            # Classificar conforto térmico
            transformed_data['comfort_level'] = self._classify_comfort(temp_c, humidity)
        
        # Adicionar qualidade dos dados
        transformed_data['data_quality_score'] = self._calculate_quality_score(transformed_data)
        
        return transformed_data
    
    def _calculate_heat_index(self, temp_f: float, humidity: float) -> float:
        """Calcula o índice de calor usando a fórmula do NOAA"""
        if temp_f < 80:
            return temp_f
        
        # Fórmula completa do heat index
        hi = (0.5 * (temp_f + 61.0 + ((temp_f - 68.0) * 1.2) + (humidity * 0.094)))
        
        if hi >= 80:
            # Fórmula mais precisa para temperaturas altas
            hi = (-42.379 + 2.04901523 * temp_f + 10.14333127 * humidity
                  - 0.22475541 * temp_f * humidity - 0.00683783 * temp_f**2
                  - 0.05481717 * humidity**2 + 0.00122874 * temp_f**2 * humidity
                  + 0.00085282 * temp_f * humidity**2 - 0.00000199 * temp_f**2 * humidity**2)
        
        return hi
    
    def _calculate_dew_point(self, temp_c: float, humidity: float) -> float:
        """Calcula o ponto de orvalho"""
        a = 17.27
        b = 237.7
        
        alpha = ((a * temp_c) / (b + temp_c)) + math.log(humidity / 100.0)
        dew_point = (b * alpha) / (a - alpha)
        
        return round(dew_point, 2)
    
    def _classify_comfort(self, temp_c: float, humidity: float) -> str:
        """Classifica o nível de conforto térmico"""
        if temp_c < 18:
            return "cold"
        elif temp_c > 26:
            if humidity > 70:
                return "hot_humid"
            else:
                return "hot"
        elif 20 <= temp_c <= 24 and 40 <= humidity <= 60:
            return "comfortable"
        elif humidity > 70:
            return "humid"
        else:
            return "mild"
    
    def _calculate_quality_score(self, data: Dict[str, Any]) -> float:
        """Calcula score de qualidade dos dados (0-100)"""
        score = 100.0
        
        # Penalizar por erros de validação
        if 'validation' in data:
            validation = data['validation']
            score -= len(validation.get('errors', [])) * 25
            score -= len(validation.get('warnings', [])) * 10
        
        # Penalizar se campos essenciais estão faltando
        essential_fields = ['temperature', 'humidity', 'device_id']
        missing_fields = [field for field in essential_fields if field not in data]
        score -= len(missing_fields) * 15
        
        return max(0.0, score)

class OutlierDetector:
    """Detector de outliers usando método IQR"""
    
    def __init__(self, recent_data: List[Dict[str, Any]]):
        self.recent_data = recent_data
    
    def detect_temperature_outliers(self, current_temp: float) -> bool:
        """Detecta outliers na temperatura"""
        if len(self.recent_data) < 10:  # Dados insuficientes
            return False
        
        temps = [d['temperature'] for d in self.recent_data if 'temperature' in d]
        if len(temps) < 10:
            return False
        
        return self._is_outlier(current_temp, temps)
    
    def detect_humidity_outliers(self, current_humidity: float) -> bool:
        """Detecta outliers na umidade"""
        if len(self.recent_data) < 10:
            return False
        
        humidities = [d['humidity'] for d in self.recent_data if 'humidity' in d]
        if len(humidities) < 10:
            return False
        
        return self._is_outlier(current_humidity, humidities)
    
    def _is_outlier(self, value: float, dataset: List[float]) -> bool:
        """Detecta outlier usando método IQR"""
        q1 = statistics.quantiles(dataset, n=4)[0]  # Q1
        q3 = statistics.quantiles(dataset, n=4)[2]  # Q3
        iqr = q3 - q1
        
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        return value < lower_bound or value > upper_bound
