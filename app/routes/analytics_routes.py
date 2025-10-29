from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_db
from app.services.analytics_service import SensorAnalyticsService
from app.processors.etl_pipeline import SensorETLPipeline, MongoDataRepository
import logging

router = APIRouter(prefix="/analytics", tags=["Analytics"])
logger = logging.getLogger(__name__)

@router.get("/summary")
async def get_analytics_summary(
    timeframe: str = Query("24h", description="Período: 1h, 6h, 24h, 7d, 30d"),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Retorna métricas agregadas para o período especificado.
    
    Inclui: médias, mínimas, máximas de temperatura e umidade,
    scores de qualidade e detecção de outliers.
    """
    try:
        analytics_service = SensorAnalyticsService(db)
        summary = await analytics_service.calculate_aggregates(timeframe)
        return summary
    
    except Exception as e:
        logger.error(f"❌ Erro ao gerar resumo analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trends")
async def get_trends_analysis(
    days: int = Query(7, description="Número de dias para análise de tendências"),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Análise de tendências de temperatura e umidade.
    
    Detecta se os valores estão aumentando, diminuindo ou estáveis
    ao longo do período especificado.
    """
    try:
        if days < 1 or days > 90:
            raise HTTPException(status_code=400, detail="Days must be between 1 and 90")
        
        analytics_service = SensorAnalyticsService(db)
        trends = await analytics_service.detect_trends(days)
        return trends
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao analisar tendências: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/data-quality")
async def get_data_quality_report(db: AsyncIOMotorDatabase = Depends(get_db)):
    """
    Relatório completo de qualidade dos dados.
    
    Inclui: estatísticas de validação, outliers detectados,
    scores de qualidade e recomendações de melhoria.
    """
    try:
        analytics_service = SensorAnalyticsService(db)
        quality_report = await analytics_service.get_data_quality_report()
        return quality_report
    
    except Exception as e:
        logger.error(f"❌ Erro ao gerar relatório de qualidade: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pipeline-stats")
async def get_pipeline_statistics(db: AsyncIOMotorDatabase = Depends(get_db)):
    """
    Estatísticas do pipeline ETL.
    
    Mostra métricas de processamento, taxa de sucesso,
    outliers detectados e performance geral.
    """
    try:
        # Para demonstrar as estatísticas, vamos criar uma instância temporária
        repository = MongoDataRepository(db)
        pipeline = SensorETLPipeline(repository)
        
        # Note: Em uma implementação real, estas estatísticas seriam
        # mantidas em um singleton ou cache para persistir entre requests
        stats = pipeline.get_stats()
        
        return {
            "message": "Pipeline statistics (session-based)",
            "note": "Statistics reset with each new pipeline instance",
            "stats": stats,
            "recommendations": [
                "Implement persistent statistics storage for production use",
                "Consider using Redis or database for pipeline metrics",
                "Add real-time monitoring dashboard"
            ]
        }
    
    except Exception as e:
        logger.error(f"❌ Erro ao obter estatísticas do pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard")
async def get_dashboard_data(db: AsyncIOMotorDatabase = Depends(get_db)):
    """
    Dados consolidados para dashboard principal.
    
    Combina métricas essenciais, tendências recentes e
    status de qualidade dos dados em uma resposta única.
    """
    try:
        analytics_service = SensorAnalyticsService(db)
        
        # Buscar dados em paralelo (se necessário, pode usar asyncio.gather)
        recent_summary = await analytics_service.calculate_aggregates("24h")
        trends_week = await analytics_service.detect_trends(7)
        quality_report = await analytics_service.get_data_quality_report()
        
        return {
            "dashboard_generated_at": recent_summary.get("period", {}).get("end"),
            "current_metrics": {
                "temperature": recent_summary.get("temperature", {}),
                "humidity": recent_summary.get("humidity", {}),
                "heat_index": recent_summary.get("heat_index", {}),
                "data_quality_score": recent_summary.get("data_quality", {}).get("average_score", 0)
            },
            "trends": {
                "temperature": trends_week.get("temperature_trend", {}),
                "humidity": trends_week.get("humidity_trend", {})
            },
            "alerts": {
                "outliers_detected": quality_report.get("outliers", {}).get("total_outliers", 0),
                "data_freshness": quality_report.get("overview", {}).get("data_freshness", "unknown"),
                "recommendations": quality_report.get("recommendations", [])
            },
            "summary": {
                "total_readings": quality_report.get("overview", {}).get("total_readings", 0),
                "recent_readings_24h": quality_report.get("overview", {}).get("recent_readings_24h", 0),
                "outlier_rate": recent_summary.get("data_quality", {}).get("outlier_rate_percent", 0)
            }
        }
    
    except Exception as e:
        logger.error(f"❌ Erro ao gerar dados do dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))
