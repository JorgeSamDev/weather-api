# Weather API REST - Flask + OpenWeather

API REST construida con Flask que consume la API de OpenWeather para obtener datos meteorológicos en tiempo real.

## 🚀 Características

✅ **4 Endpoints REST** para consultar datos meteorológicos  
✅ **Validaciones completas** de parámetros de entrada  
✅ **Manejo robusto de errores** (401, 404, 503, timeouts)  
✅ **Respuestas JSON limpias** y bien estructuradas  
✅ **Soporte para múltiples ciudades** en una sola solicitud  
✅ **Búsqueda por coordenadas** (latitud/longitud)  

## 📋 Requisitos

- Python 3.8+
- Las dependencias están en `requirements.txt`:
  - Flask 3.0.0
  - requests 2.31.0
  - python-dotenv 1.0.0

## 🔧 Instalación

### 1. Clonar/descargar el proyecto

```bash
cd weather-api
```

### 2. Crear un entorno virtual (recomendado)

```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar la API key

Obtén una API key gratuita en [OpenWeather API](https://openweathermap.org/api)

Edita el archivo `.env` y reemplaza:
```
OPENWEATHER_API_KEY=tu_api_key_aqui
```

### 5. Ejecutar la aplicación

```bash
python app.py
```

La API estará disponible en: `http://localhost:5000`

## 📡 Endpoints

### 1. GET `/health`
Verificar que el servicio está activo y la API key está configurada

**Request:**
```bash
curl http://localhost:5000/health
```

**Response (200):**
```json
{
  "status": "healthy",
  "service": "Weather API",
  "api_key_configured": true
}
```

---

### 2. GET `/`
Información general de la API

**Request:**
```bash
curl http://localhost:5000/
```

**Response (200):**
```json
{
  "name": "Weather API",
  "version": "1.0.0",
  "description": "API REST que consume OpenWeather API",
  "endpoints": {
    "GET /health": "Verificar estado del servicio",
    "GET /": "Información de la API",
    "GET /weather": "Obtener clima por ciudad o coordenadas",
    "POST /weather/multiple": "Obtener clima para múltiples ciudades"
  },
  "query_parameters": {
    "city": "Nombre de la ciudad (ej: Madrid)",
    "lat": "Latitud (ej: 40.4168)",
    "lon": "Longitud (ej: -3.7038)"
  }
}
```

---

### 3. GET `/weather`
Obtener clima de una ciudad o por coordenadas

**Parámetros:**
- `city` (string): Nombre de la ciudad
- `lat` (float): Latitud (-90 a 90)
- `lon` (float): Longitud (-180 a 180)

**Ejemplo 1 - Por ciudad:**
```bash
curl "http://localhost:5000/weather?city=Madrid"
```

**Ejemplo 2 - Por coordenadas:**
```bash
curl "http://localhost:5000/weather?lat=40.4168&lon=-3.7038"
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "city": "Madrid",
    "country": "ES",
    "coordinates": {
      "lat": 40.4168,
      "lon": -3.7038
    },
    "weather": {
      "main": "Clouds",
      "description": "overcast clouds",
      "icon": "04d"
    },
    "temperature": {
      "current": 22.5,
      "feels_like": 21.8,
      "min": 20.1,
      "max": 24.3
    },
    "atmospheric": {
      "pressure": 1013,
      "humidity": 65,
      "visibility": 10000
    },
    "wind": {
      "speed": 3.5,
      "degree": 240,
      "gust": 5.2
    },
    "clouds": 90,
    "timestamp": 1717338543,
    "sunrise": 1717307425,
    "sunset": 1717359876
  }
}
```

**Errores posibles:**

- **400** - Parámetros inválidos:
```json
{
  "error": "Bad Request",
  "message": "Debes proporcionar \"city\" o ambos \"lat\" y \"lon\""
}
```

- **401** - API key inválida:
```json
{
  "error": "Unauthorized",
  "message": "API key inválida o expirada",
  "status_code": 401
}
```

- **404** - Ciudad no encontrada:
```json
{
  "error": "Not Found",
  "message": "La ciudad o ubicación no fue encontrada",
  "status_code": 404
}
```

- **504** - Timeout:
```json
{
  "error": "Timeout",
  "message": "La solicitud tardó más de 5 segundos",
  "status_code": 504
}
```

---

### 4. POST `/weather/multiple`
Obtener clima para múltiples ciudades y/o coordenadas

**Body JSON:**
```json
{
  "cities": ["Madrid", "Barcelona", "Valencia"],
  "coordinates": [
    {"lat": 40.4168, "lon": -3.7038},
    {"lat": 41.3851, "lon": 2.1734}
  ]
}
```

**Request:**
```bash
curl -X POST http://localhost:5000/weather/multiple \
  -H "Content-Type: application/json" \
  -d '{
    "cities": ["Madrid", "Barcelona"],
    "coordinates": [{"lat": 40.4168, "lon": -3.7038}]
  }'
```

**Response (200):**
```json
{
  "success": true,
  "count": 3,
  "weather": [
    {
      "city": "Madrid",
      "country": "ES",
      "coordinates": {"lat": 40.4168, "lon": -3.7038},
      "weather": {"main": "Clouds", "description": "overcast clouds", "icon": "04d"},
      "temperature": {"current": 22.5, "feels_like": 21.8, "min": 20.1, "max": 24.3},
      ...
    },
    {
      "city": "Barcelona",
      "country": "ES",
      ...
    }
  ],
  "errors": []
}
```

**Con errores:**
```json
{
  "success": true,
  "count": 2,
  "weather": [...],
  "errors": [
    {
      "location": "CiudadInexistente",
      "error": "Not Found",
      "message": "La ciudad o ubicación no fue encontrada"
    }
  ]
}
```

## 🔒 Validaciones Implementadas

| Validación | Descripción |
|-----------|-------------|
| API Key | Verifica que OPENWEATHER_API_KEY está configurada |
| Ciudad | No puede estar vacía |
| Latitud | Debe estar entre -90 y 90 |
| Longitud | Debe estar entre -180 y 180 |
| Coordenadas | Ambas (lat, lon) son requeridas juntas |
| JSON | Valida el formato del body en POST |
| Límite | Máximo 20 ubicaciones en múltiples |

## ⚠️ Manejo de Errores

| Código | Error | Causas |
|--------|-------|--------|
| 400 | Bad Request | Parámetros inválidos |
| 401 | Unauthorized | API key inválida |
| 404 | Not Found | Ciudad/ubicación no existe |
| 429 | Too Many Requests | Límite de solicitudes excedido |
| 503 | Service Unavailable | Servidor de OpenWeather caído |
| 504 | Gateway Timeout | Solicitud tardó > 5s |

## 🐳 Ejecutar con Docker

```bash
docker build -t weather-api .
docker run -p 5000:5000 -e OPENWEATHER_API_KEY=tu_key weather-api
```

## 📝 Variables de Entorno

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| OPENWEATHER_API_KEY | Clave de API de OpenWeather | `abc123def456` |

## 🧪 Pruebas Rápidas

```bash
# Health check
curl http://localhost:5000/health

# Madrid
curl "http://localhost:5000/weather?city=Madrid"

# Coordenadas de París
curl "http://localhost:5000/weather?lat=48.8566&lon=2.3522"

# Múltiples ciudades
curl -X POST http://localhost:5000/weather/multiple \
  -H "Content-Type: application/json" \
  -d '{"cities": ["London", "Tokyo", "Sydney"]}'
```

## 📚 Documentación de OpenWeather API

- [Documentación oficial](https://openweathermap.org/api)
- [Plan gratuito](https://openweathermap.org/api/free)
- [Códigos de clima](https://openweathermap.org/weather-conditions)

## 🐛 Troubleshooting

### Error: "OPENWEATHER_API_KEY no está configurada"
✅ Solución: Crear archivo `.env` con la API key

### Error: 401 Unauthorized
✅ Solución: Verificar que la API key es válida

### Error: 404 Not Found
✅ Solución: Verificar que el nombre de la ciudad existe

### Error: Timeout
✅ Solución: Verificar conexión a internet, reintentar

## 📄 Licencia

Este proyecto es de código abierto.

## 👨‍💻 Autor

Creado como ejercicio de API REST con Flask y OpenWeather API.
