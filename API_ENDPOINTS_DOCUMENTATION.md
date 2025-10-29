# 📡 API Endpoints Documentation - Smart Bus IoT

Esta documentação contém todos os endpoints disponíveis na API para integração com frontend e dispositivos IoT.

**Base URL**: `http://localhost:8001`

---

## 🔐 **Autenticação** (`/api/auth`)

### `POST /api/auth/register`
**Descrição:** Registra novo usuário
```json
// Request Body
{
  "email": "user@example.com",
  "password": "mypassword",
  "full_name": "João Silva" // opcional
}

// Response (200)
{
  "msg": "User created",
  "user_id": "507f1f77bcf86cd799439011"
}

// Response (400) - Email já existe
{
  "detail": "Email already registered"
}
```

### `POST /api/auth/login`
**Descrição:** Login do usuário
```json
// Request Body
{
  "email": "user@example.com",
  "password": "mypassword"
}

// Response (200)
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}

// Response (401) - Credenciais inválidas
{
  "detail": "Invalid credentials"
}
```

---

## 🌡️ **Sensores IoT** (`/api/sensors`)

### `POST /api/sensors/ingest`
**Descrição:** Recebe dados do sensor ESP32 (pipeline ETL automático)
```json
// Headers
{
  "iot-api-key": "smartbus_esp32_key_2024",
  "Content-Type": "application/json"
}

// Request Body
{
  "temperature": 25.5,
  "humidity": 60.2,
  "device_id": "ESP32_001" // opcional
}

// Response (200) - Sucesso
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

// Response (401) - Chave IoT inválida
{
  "detail": "Chave IoT inválida."
}

// Response (500) - Erro no processamento
{
  "detail": "Error message"
}
```

### `GET /api/sensors/readings`
**Descrição:** Lista últimas leituras dos sensores
```json
// Query Parameters
{
  "limit": 10 // opcional, padrão: 10
}

// Response (200)
{
  "readings": [
    {
      "id": "507f1f77bcf86cd799439011",
      "temperature": 25.5,
      "humidity": 60.2,
      "device_id": "ESP32_001",
      "recorded_at": "2025-01-28T10:00:00Z",
      "processed_at": "2025-01-28T10:00:01Z",
      "heat_index": 27.3,
      "dew_point": 17.8,
      "comfort_level": "comfortable",
      "data_quality_score": 95.0,
      "is_temperature_outlier": false,
      "is_humidity_outlier": false,
      "validation": {
        "is_valid": true,
        "errors": [],
        "warnings": []
      }
    }
  ],
  "count": 1
}
```

### `GET /api/sensors/test_thingspeak`
**Descrição:** Teste manual do ThingSpeak
```json
// Query Parameters
{
  "temperature": 25.0, // opcional, padrão: 25.0
  "humidity": 60.0     // opcional, padrão: 60.0
}

// Response (200) - Sucesso
{
  "status": "success",
  "message": "Dados enviados ao ThingSpeak: 25.0°C / 60.0%"
}

// Response (400) - Falha no envio
{
  "detail": "Falha ao enviar ao ThingSpeak."
}
```

---

## 📊 **Analytics & Big Data** (`/api/analytics`)

### `GET /api/analytics/summary`
**Descrição:** Métricas agregadas por período
```json
// Query Parameters
{
  "timeframe": "24h" // 1h, 6h, 24h, 7d, 30d
}

// Response (200)
{
  "timeframe": "24h",
  "period": {
    "start": "2025-01-27T10:00:00Z",
    "end": "2025-01-28T10:00:00Z"
  },
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
  "heat_index": {
    "average": 27.8
  },
  "data_quality": {
    "average_score": 92.5,
    "total_readings": 144,
    "outliers_detected": 3,
    "outlier_rate_percent": 2.1
  }
}
```

### `GET /api/analytics/trends`
**Descrição:** Análise de tendências temporais
```json
// Query Parameters
{
  "days": 7 // 1-90 dias
}

// Response (200)
{
  "period": {
    "start": "2025-01-21T10:00:00Z",
    "end": "2025-01-28T10:00:00Z",
    "days": 7
  },
  "data_points": 168,
  "temperature_trend": {
    "direction": "increasing", // "increasing", "decreasing", "stable"
    "slope": 0.0234,
    "interpretation": "temperature is slightly increasing"
  },
  "humidity_trend": {
    "direction": "stable",
    "slope": -0.0012,
    "interpretation": "humidity remains stable"
  }
}

// Response (400) - Parâmetro inválido
{
  "detail": "Days must be between 1 and 90"
}
```

### `GET /api/analytics/data-quality`
**Descrição:** Relatório de qualidade dos dados
```json
// Response (200)
{
  "generated_at": "2025-01-28T10:00:00Z",
  "overview": {
    "total_readings": 1520,
    "recent_readings_24h": 144,
    "data_freshness": "good" // "good", "stale"
  },
  "data_quality": {
    "average_score": 94.2,
    "minimum_score": 75.0,
    "maximum_score": 100.0
  },
  "validation_issues": {
    "invalid_records": 12,
    "common_errors": [
      {
        "_id": ["temperature_out_of_range"],
        "count": 8
      },
      {
        "_id": ["humidity_very_high"],
        "count": 4
      }
    ]
  },
  "outliers": {
    "temperature_outliers": 15,
    "humidity_outliers": 8,
    "total_outliers": 23
  },
  "recommendations": [
    "Data quality is good. Continue monitoring for optimal performance."
  ]
}
```

### `GET /api/analytics/pipeline-stats`
**Descrição:** Estatísticas do pipeline ETL
```json
// Response (200)
{
  "message": "Pipeline statistics (session-based)",
  "note": "Statistics reset with each new pipeline instance",
  "stats": {
    "processed": 156,
    "valid": 142,
    "invalid": 14,
    "outliers": 8,
    "success_rate": 91.0,
    "outlier_rate": 5.1
  },
  "recommendations": [
    "Implement persistent statistics storage for production use",
    "Consider using Redis or database for pipeline metrics",
    "Add real-time monitoring dashboard"
  ]
}
```

### `GET /api/analytics/dashboard`
**Descrição:** Dashboard consolidado com todas as métricas principais
```json
// Response (200)
{
  "dashboard_generated_at": "2025-01-28T10:00:00Z",
  "current_metrics": {
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
    "heat_index": {
      "average": 27.8
    },
    "data_quality_score": 92.5
  },
  "trends": {
    "temperature": {
      "direction": "increasing",
      "slope": 0.0234,
      "interpretation": "temperature is slightly increasing"
    },
    "humidity": {
      "direction": "stable",
      "slope": -0.0012,
      "interpretation": "humidity remains stable"
    }
  },
  "alerts": {
    "outliers_detected": 23,
    "data_freshness": "good",
    "recommendations": [
      "Data quality is good. Continue monitoring for optimal performance."
    ]
  },
  "summary": {
    "total_readings": 1520,
    "recent_readings_24h": 144,
    "outlier_rate": 2.1
  }
}
```

---

## 🏠 **Raiz da API**

### `GET /`
**Descrição:** Endpoint raiz da API
```json
// Response (200)
{
  "message": "Smart Bus Stop API 🚌"
}
```

---

## 🔧 **Headers e Autenticação**

### Para endpoints de sensores IoT:
```bash
Headers:
iot-api-key: smartbus_esp32_key_2024
Content-Type: application/json
```

### Para endpoints autenticados (se implementado):
```bash
Headers:
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

---

## 📝 **Códigos de Status HTTP**

- **200**: Sucesso
- **400**: Erro de validação/parâmetros inválidos
- **401**: Não autorizado (chave IoT inválida ou token JWT inválido)
- **404**: Endpoint não encontrado
- **500**: Erro interno do servidor

---

## 🚀 **Exemplos de Integração Frontend**

### React/JavaScript - Buscar dados do dashboard:
```javascript
const fetchDashboard = async () => {
  try {
    const response = await fetch('/api/analytics/dashboard');
    const data = await response.json();
    console.log('Dashboard data:', data);
  } catch (error) {
    console.error('Error fetching dashboard:', error);
  }
};
```

### React/JavaScript - Enviar dados do sensor:
```javascript
const sendSensorData = async (temperature, humidity) => {
  const sensorData = {
    temperature: temperature,
    humidity: humidity,
    device_id: "ESP32_001"
  };

  try {
    const response = await fetch('/api/sensors/ingest', {
      method: 'POST',
      headers: {
        'iot-api-key': 'smartbus_esp32_key_2024',
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(sensorData)
    });
    
    const result = await response.json();
    console.log('Sensor data sent:', result);
  } catch (error) {
    console.error('Error sending sensor data:', error);
  }
};
```

### React/JavaScript - Buscar leituras dos sensores:
```javascript
const fetchSensorReadings = async (limit = 10) => {
  try {
    const response = await fetch(`/api/sensors/readings?limit=${limit}`);
    const data = await response.json();
    console.log('Sensor readings:', data.readings);
  } catch (error) {
    console.error('Error fetching readings:', error);
  }
};
```

### React/JavaScript - Login e autenticação:
```javascript
const login = async (email, password) => {
  try {
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ email, password })
    });
    
    const data = await response.json();
    
    if (response.ok) {
      // Salvar token para usar em requisições futuras
      localStorage.setItem('token', data.access_token);
      console.log('Login successful');
    } else {
      console.error('Login failed:', data.detail);
    }
  } catch (error) {
    console.error('Login error:', error);
  }
};
```

### React/JavaScript - Buscar análise de tendências:
```javascript
const fetchTrends = async (days = 7) => {
  try {
    const response = await fetch(`/api/analytics/trends?days=${days}`);
    const data = await response.json();
    console.log('Trends analysis:', data);
  } catch (error) {
    console.error('Error fetching trends:', error);
  }
};
```

### React/JavaScript - Buscar métricas agregadas:
```javascript
const fetchSummary = async (timeframe = '24h') => {
  try {
    const response = await fetch(`/api/analytics/summary?timeframe=${timeframe}`);
    const data = await response.json();
    console.log('Analytics summary:', data);
  } catch (error) {
    console.error('Error fetching summary:', error);
  }
};
```

---

## 📋 **Fluxo Recomendado para Frontend**

1. **Inicialização**: Chamar `GET /` para verificar se API está online
2. **Dashboard Principal**: Chamar `GET /api/analytics/dashboard` para dados consolidados
3. **Leituras em Tempo Real**: Chamar `GET /api/sensors/readings` periodicamente
4. **Análises Detalhadas**: Usar endpoints específicos de analytics conforme necessário
5. **Autenticação**: Implementar login/register se necessário para funcionalidades administrativas

---

## 🎯 **Endpoints Prioritários para Frontend**

Para uma implementação inicial, recomendo focar nestes endpoints:

1. **`GET /api/analytics/dashboard`** - Dados principais do dashboard
2. **`GET /api/sensors/readings`** - Leituras atuais dos sensores
3. **`GET /api/analytics/summary`** - Métricas por período
4. **`GET /api/analytics/trends`** - Análise de tendências
5. **`POST /api/sensors/ingest`** - Para testes de envio de dados