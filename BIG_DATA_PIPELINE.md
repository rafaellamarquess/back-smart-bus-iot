# 🚌 Smart Bus IoT - Big Data Pipeline

## 📋 Visão Geral

Este projeto implementa uma **pipeline completa de Big Data** para coleta, processamento e análise de dados IoT de sensores de temperatura e umidade. O sistema segue os **princípios SOLID** e implementa tratamento avançado de dados antes do armazenamento no MongoDB.

## 🏗️ Arquitetura da Solução

### Pipeline ETL Automatizada
```
Sensor IoT → API /ingest → [ETL Pipeline] → MongoDB + ThingSpeak
                              ↓
                     [Extract → Transform → Load]
                              ↓
                     [Validate → Enrich → Store]
```

### Componentes Principais

#### 1. **Interfaces Abstratas (SOLID)**
- `DataValidator` - Validação de dados
- `DataTransformer` - Transformação e enriquecimento
- `DataProcessor` - Processamento principal
- `DataRepository` - Persistência de dados
- `AnalyticsService` - Serviços de análise
- `ETLPipeline` - Pipeline ETL

#### 2. **Processamento de Dados**
- **Validação**: Limites de temperatura (-40°C a 80°C) e umidade (0-100%)
- **Detecção de Outliers**: Método IQR (Interquartile Range)
- **Enriquecimento**: Cálculo de heat index, ponto de orvalho, nível de conforto
- **Qualidade**: Score de qualidade dos dados (0-100)

#### 3. **Pipeline ETL**
- **Extract**: Recebe dados do sensor IoT
- **Transform**: Valida, detecta outliers, enriquece dados
- **Load**: Salva no MongoDB com metadados completos

## 🔧 Endpoints da API

### Sensores IoT
- `POST /api/sensors/ingest` - Recebe dados do sensor (com pipeline ETL)
- `GET /api/sensors/readings` - Lista leituras armazenadas
- `GET /api/sensors/test_thingspeak` - Teste de integração ThingSpeak

### Analytics & Big Data
- `GET /api/analytics/summary?timeframe=24h` - Métricas agregadas
- `GET /api/analytics/trends?days=7` - Análise de tendências
- `GET /api/analytics/data-quality` - Relatório de qualidade
- `GET /api/analytics/pipeline-stats` - Estatísticas do pipeline
- `GET /api/analytics/dashboard` - Dashboard consolidado

### Autenticação
- `POST /api/auth/register` - Registrar usuário
- `POST /api/auth/login` - Login de usuário

## 📊 Funcionalidades de Big Data

### 1. **Tratamento e Limpeza de Dados**
- ✅ Validação de tipos e limites
- ✅ Detecção de outliers estatísticos
- ✅ Classificação de qualidade dos dados
- ✅ Tratamento de dados inconsistentes

### 2. **Enriquecimento de Dados**
- ✅ Cálculo de heat index (índice de calor)
- ✅ Cálculo de ponto de orvalho
- ✅ Classificação de conforto térmico
- ✅ Timestamps de processamento

### 3. **Analytics Avançado**
- ✅ Agregações temporais (1h, 6h, 24h, 7d, 30d)
- ✅ Análise de tendências com regressão linear
- ✅ Relatórios de qualidade de dados
- ✅ Dashboard consolidado

### 4. **Princípios SOLID Aplicados**
- **S** - Single Responsibility: Cada classe tem uma responsabilidade específica
- **O** - Open/Closed: Interfaces extensíveis sem modificar código existente
- **L** - Liskov Substitution: Implementações substituíveis via interfaces
- **I** - Interface Segregation: Interfaces específicas para cada funcionalidade
- **D** - Dependency Inversion: Dependências abstratas via injeção

## 🚀 Como Usar

### 1. **Enviar Dados do Sensor**
```bash
POST /api/sensors/ingest
Headers: 
  iot-api-key: smartbus_esp32_key_2024
  Content-Type: application/json

Body:
{
  "temperature": 25.5,
  "humidity": 60.2,
  "device_id": "ESP32_001"
}
```

**Resposta com Pipeline ETL:**
```json
{
  "status": "ok",
  "id": "507f1f77bcf86cd799439011",
  "etl_pipeline": {
    "executed": true,
    "data_quality_score": 95.0,
    "outliers_detected": {
      "temperature": false,
      "humidity": false
    },
    "processed_fields": {
      "heat_index": true,
      "dew_point": true,
      "comfort_level": true
    }
  }
}
```

### 2. **Obter Analytics**
```bash
GET /api/analytics/summary?timeframe=24h
```

**Resposta:**
```json
{
  "timeframe": "24h",
  "temperature": {
    "average": 25.3,
    "minimum": 18.2,
    "maximum": 32.1
  },
  "humidity": {
    "average": 65.4,
    "minimum": 45.0,
    "maximum": 85.0
  },
  "data_quality": {
    "average_score": 92.5,
    "outliers_detected": 3,
    "outlier_rate_percent": 1.2
  }
}
```

### 3. **Dashboard Consolidado**
```bash
GET /api/analytics/dashboard
```

## 📈 Dados Processados

### Exemplo de Dado Enriquecido no MongoDB:
```json
{
  "_id": "507f1f77bcf86cd799439011",
  "temperature": 28.5,
  "humidity": 70.0,
  "device_id": "ESP32_001",
  "recorded_at": "2025-10-28T10:00:00Z",
  "processed_at": "2025-10-28T10:00:01Z",
  "heat_index": 32.4,
  "dew_point": 22.1,
  "comfort_level": "hot_humid",
  "data_quality_score": 100.0,
  "is_temperature_outlier": false,
  "is_humidity_outlier": false,
  "validation": {
    "is_valid": true,
    "errors": [],
    "warnings": []
  }
}
```

## 🏆 Diferenciais Implementados

### ✅ **Organização da Solução**
- Estrutura modular seguindo Clean Architecture
- Separação clara de responsabilidades
- Interfaces bem definidas

### ✅ **Princípios SOLID**
- Todas as interfaces abstratas implementadas
- Injeção de dependências
- Código extensível e testável

### ✅ **Tratamento e Limpeza de Dados**
- Pipeline ETL automatizado
- Validação rigorosa de dados
- Detecção de outliers estatísticos
- Enriquecimento automático

### ✅ **Automação ETL**
- Extração automática dos dados IoT
- Transformação inteligente com validações
- Carregamento otimizado no MongoDB

## 📁 Estrutura do Projeto

```
app/
├── core/           # Configurações e segurança
├── models/         # Modelos de dados
├── schemas/        # Schemas Pydantic
├── routes/         # Endpoints da API
├── services/       # Serviços externos
├── processors/     # 🆕 Pipeline ETL e processamento
├── interfaces/     # 🆕 Interfaces abstratas (SOLID)
├── crud/          # Operações de banco
└── utils/         # Utilitários
```

## 🔍 Monitoramento e Qualidade

- **Score de Qualidade**: 0-100 baseado em validações
- **Detecção de Outliers**: Método IQR estatístico
- **Relatórios**: Analytics completos de qualidade
- **Tendências**: Análise temporal com regressão linear
- **Dashboard**: Consolidação de métricas principais

---

## 📚 Documentação Técnica

### Validações Implementadas:
- Temperatura: -40°C a 80°C (com warnings para extremos)
- Umidade: 0% a 100% (com warnings acima de 95%)
- Tipos de dados obrigatórios
- Campos obrigatórios

### Cálculos Científicos:
- **Heat Index**: Fórmula NOAA para índice de calor
- **Dew Point**: Cálculo do ponto de orvalho
- **Comfort Level**: Classificação de conforto térmico

### Analytics Estatísticos:
- Médias, mínimas, máximas
- Regressão linear para tendências
- Quartis para detecção de outliers
- Agregações temporais flexíveis

Esta implementação atende completamente aos requisitos do projeto, combinando IoT e Big Data com uma arquitetura robusta e escalável! 🚀
