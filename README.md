# 🚌 Smart Bus IoT Backend

**Smart Bus IoT** é um sistema de monitoramento inteligente para sensores embarcados em veículos, integrando dados de temperatura e umidade coletados via **ESP32 + DHT11** e armazenados em tempo real no **MongoDB**, através de uma API desenvolvida com **FastAPI** e um pipeline ETL assíncrono.

---

### Tecnologias Principais

| - | Tecnologias |
|--------|--------------|
| IoT | ESP32, DHT11, C++ (Arduino) |
| Backend | Python, FastAPI, asyncio |
| Banco de Dados | MongoDB (Atlas) |
| Integrações | ThingSpeak API |
| Processamento | ETL Pipeline (Extração, Transformação, Carga) |

---

### Funcionalidades

- **Coleta automática de dados IoT** (temperatura e umidade) via ThingSpeak.
- **Pipeline ETL assíncrono**:
  - Extração de dados do ThingSpeak.
  - Validação e transformação (detecção de outliers, cálculo de índice de calor, ponto de orvalho e nível de conforto térmico).
  - Armazenamento otimizado no MongoDB.

---

### Fluxo de Dados

**1. Coleta (ESP32)**
O microcontrolador lê temperatura e umidade, enviando a cada 30s para o canal ThingSpeak via HTTP.

**2. Consumo (Backend)**
O serviço `ThingSpeakConsumerService` busca novos `entry_id`s no canal e os envia para o pipeline.

**3. Processamento (ETL)**
O pipeline valida, transforma e grava os dados, calculando métricas adicionais e ignorando duplicatas.
