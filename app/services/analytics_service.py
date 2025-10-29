import statistics
from typing import Dict, Any, List
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging

from app.interfaces.data_interfaces import AnalyticsService

logger = logging.getLogger(__name__)

class SensorAnalyticsService(AnalyticsService):
    """Serviço de analytics para dados de sensores IoT"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.sensor_readings
    
    async def calculate_aggregates(self, timeframe: str = "1h") -> Dict[str, Any]:
        """Calcula métricas agregadas para um período"""
        # Definir período de tempo
        now = datetime.utcnow()
        time_deltas = {
            "1h": timedelta(hours=1),
            "6h": timedelta(hours=6),
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30)
        }
        
        start_time = now - time_deltas.get(timeframe, timedelta(hours=1))
        
        # Pipeline de agregação MongoDB
        pipeline = [
            {
                "$match": {
                    "recorded_at": {"$gte": start_time},
                    "validation.is_valid": True
                }
            },
            {
                "$group": {
                    "_id": None,
                    "avg_temperature": {"$avg": "$temperature"},
                    "min_temperature": {"$min": "$temperature"},
                    "max_temperature": {"$max": "$temperature"},
                    "avg_humidity": {"$avg": "$humidity"},
                    "min_humidity": {"$min": "$humidity"},
                    "max_humidity": {"$max": "$humidity"},
                    "avg_heat_index": {"$avg": "$heat_index"},
                    "avg_data_quality": {"$avg": "$data_quality_score"},
                    "total_readings": {"$sum": 1},
                    "outliers": {
                        "$sum": {
                            "$cond": [
                                {"$or": ["$is_temperature_outlier", "$is_humidity_outlier"]},
                                1,
                                0
                            ]
                        }
                    }
                }
            }
        ]
        
        try:
            result = await self.collection.aggregate(pipeline).to_list(1)
            
            if not result:
                return {
                    "timeframe": timeframe,
                    "period": {"start": start_time, "end": now},
                    "summary": "No data available for this period",
                    "metrics": {}
                }
            
            data = result[0]
            
            # Calcular métricas adicionais
            outlier_rate = (data.get('outliers', 0) / data.get('total_readings', 1)) * 100
            
            return {
                "timeframe": timeframe,
                "period": {
                    "start": start_time.isoformat(),
                    "end": now.isoformat()
                },
                "temperature": {
                    "average": round(data.get('avg_temperature', 0), 2),
                    "minimum": round(data.get('min_temperature', 0), 2),
                    "maximum": round(data.get('max_temperature', 0), 2)
                },
                "humidity": {
                    "average": round(data.get('avg_humidity', 0), 2),
                    "minimum": round(data.get('min_humidity', 0), 2),
                    "maximum": round(data.get('max_humidity', 0), 2)
                },
                "heat_index": {
                    "average": round(data.get('avg_heat_index', 0), 2)
                },
                "data_quality": {
                    "average_score": round(data.get('avg_data_quality', 0), 2),
                    "total_readings": data.get('total_readings', 0),
                    "outliers_detected": data.get('outliers', 0),
                    "outlier_rate_percent": round(outlier_rate, 2)
                }
            }
            
        except Exception as e:
            logger.error(f"Erro ao calcular agregações: {e}")
            return {"error": str(e)}
    
    async def detect_trends(self, days: int = 7, max_points: int = 100) -> Dict[str, Any]:
        """Detecta tendências nos dados dos últimos N dias"""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        
        # Buscar dados agrupados por hora
        pipeline = [
            {
                "$match": {
                    "recorded_at": {"$gte": start_time},
                    "validation.is_valid": True
                }
            },
            {
                "$group": {
                    "_id": {
                        "year": {"$year": "$recorded_at"},
                        "month": {"$month": "$recorded_at"},
                        "day": {"$dayOfMonth": "$recorded_at"},
                        "hour": {"$hour": "$recorded_at"}
                    },
                    "avg_temperature": {"$avg": "$temperature"},
                    "avg_humidity": {"$avg": "$humidity"},
                    "readings_count": {"$sum": 1}
                }
            },
            {
                "$sort": {
                    "_id.year": 1,
                    "_id.month": 1,
                    "_id.day": 1,
                    "_id.hour": 1
                }
            },
            {"$limit": max_points}
        ]
        
        try:
            hourly_data = await self.collection.aggregate(pipeline).to_list(max_points)
            
            if len(hourly_data) < 2:
                return {"message": "Insufficient data for trend analysis"}
            
            # Extrair séries temporais
            temperatures = [item['avg_temperature'] for item in hourly_data]
            humidities = [item['avg_humidity'] for item in hourly_data]
            
            # Calcular tendências usando regressão linear simples
            temp_trend = self._calculate_trend(temperatures)
            humidity_trend = self._calculate_trend(humidities)
            
            return {
                "period": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                    "days": days
                },
                "data_points": len(hourly_data),
                "temperature_trend": {
                    "direction": "increasing" if temp_trend > 0.1 else "decreasing" if temp_trend < -0.1 else "stable",
                    "slope": round(temp_trend, 4),
                    "interpretation": self._interpret_trend(temp_trend, "temperature")
                },
                "humidity_trend": {
                    "direction": "increasing" if humidity_trend > 0.1 else "decreasing" if humidity_trend < -0.1 else "stable",
                    "slope": round(humidity_trend, 4),
                    "interpretation": self._interpret_trend(humidity_trend, "humidity")
                }
            }
            
        except Exception as e:
            logger.error(f"Erro ao detectar tendências: {e}")
            return {"error": str(e)}
    
    async def get_data_quality_report(self) -> Dict[str, Any]:
        """Gera relatório de qualidade dos dados"""
        now = datetime.utcnow()
        last_24h = now - timedelta(hours=24)
        
        try:
            # Estatísticas gerais
            total_readings = await self.collection.count_documents({})
            recent_readings = await self.collection.count_documents({"recorded_at": {"$gte": last_24h}})
            
            # Dados inválidos
            invalid_pipeline = [
                {"$match": {"validation.is_valid": False}},
                {"$group": {
                    "_id": "$validation.errors",
                    "count": {"$sum": 1}
                }},
                {"$sort": {"count": -1}}
            ]
            
            invalid_data = await self.collection.aggregate(invalid_pipeline).to_list(None)
            
            # Outliers
            outliers_temp = await self.collection.count_documents({"is_temperature_outlier": True})
            outliers_humidity = await self.collection.count_documents({"is_humidity_outlier": True})
            
            # Score médio de qualidade
            quality_pipeline = [
                {"$group": {
                    "_id": None,
                    "avg_quality_score": {"$avg": "$data_quality_score"},
                    "min_quality_score": {"$min": "$data_quality_score"},
                    "max_quality_score": {"$max": "$data_quality_score"}
                }}
            ]
            
            quality_result = await self.collection.aggregate(quality_pipeline).to_list(1)
            quality_stats = quality_result[0] if quality_result else {}
            
            def safe_round(val, ndigits=2):
                if val is None:
                    return 0.0
                return round(val, ndigits)

            return {
                "generated_at": now.isoformat(),
                "overview": {
                    "total_readings": total_readings,
                    "recent_readings_24h": recent_readings,
                    "data_freshness": "good" if recent_readings > 0 else "stale"
                },
                "data_quality": {
                    "average_score": safe_round(quality_stats.get('avg_quality_score', 0)),
                    "minimum_score": safe_round(quality_stats.get('min_quality_score', 0)),
                    "maximum_score": safe_round(quality_stats.get('max_quality_score', 0))
                },
                "validation_issues": {
                    "invalid_records": len(invalid_data),
                    "common_errors": invalid_data[:5]  # Top 5 erros mais comuns
                },
                "outliers": {
                    "temperature_outliers": outliers_temp,
                    "humidity_outliers": outliers_humidity,
                    "total_outliers": outliers_temp + outliers_humidity
                },
                "recommendations": self._generate_recommendations(quality_stats, invalid_data, outliers_temp + outliers_humidity)
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar relatório de qualidade: {e}")
            return {"error": str(e)}
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calcula tendência usando regressão linear simples"""
        if len(values) < 2:
            return 0.0
        
        n = len(values)
        x = list(range(n))
        
        # Cálculo da regressão linear y = ax + b
        sum_x = sum(x)
        sum_y = sum(values)
        sum_xy = sum(x[i] * values[i] for i in range(n))
        sum_x2 = sum(xi ** 2 for xi in x)
        
        # Coeficiente angular (slope)
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
        return slope
    
    def _interpret_trend(self, slope: float, metric: str) -> str:
        """Interpreta a tendência baseada no slope"""
        if abs(slope) < 0.1:
            return f"{metric} remains stable"
        elif slope > 0:
            magnitude = "slightly" if slope < 0.5 else "moderately" if slope < 1.0 else "significantly"
            return f"{metric} is {magnitude} increasing"
        else:
            magnitude = "slightly" if slope > -0.5 else "moderately" if slope > -1.0 else "significantly"
            return f"{metric} is {magnitude} decreasing"
    
    def _generate_recommendations(self, quality_stats: Dict, invalid_data: List, outliers_count: int) -> List[str]:
        """Gera recomendações baseadas na qualidade dos dados"""
        recommendations = []
        
        avg_quality = quality_stats.get('avg_quality_score', 100)
        
        if avg_quality < 70:
            recommendations.append("Data quality is below acceptable levels. Consider reviewing sensor calibration.")
        
        if len(invalid_data) > 10:
            recommendations.append("High number of validation errors detected. Check sensor connectivity and data transmission.")
        
        if outliers_count > 50:
            recommendations.append("Frequent outliers detected. Verify sensor placement and environmental factors.")
        
        if not recommendations:
            recommendations.append("Data quality is good. Continue monitoring for optimal performance.")
        
        return recommendations
