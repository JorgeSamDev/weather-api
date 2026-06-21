import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import requests
from typing import Dict, Any, Optional, List

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)

# Configuración
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')
OPENWEATHER_BASE_URL = 'https://api.openweathermap.org/data/2.5/weather'
OPENWEATHER_FORECAST_URL = 'https://api.openweathermap.org/data/2.5/forecast'
REQUEST_TIMEOUT = 5

# Validar que existe la API key
if not OPENWEATHER_API_KEY:
    print("⚠️  WARNING: OPENWEATHER_API_KEY no está configurada en .env")


def validate_api_key() -> tuple[bool, Dict[str, Any]]:
    """Validar que la API key está configurada"""
    if not OPENWEATHER_API_KEY:
        return False, {
            'error': 'API key no configurada',
            'message': 'OPENWEATHER_API_KEY no está definida en .env'
        }
    return True, {}


def make_weather_request(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Hacer una solicitud a OpenWeather API con manejo de errores
    
    Args:
        params: Parámetros para la solicitud
        
    Returns:
        Dict con los datos del clima o error
    """
    try:
        response = requests.get(
            OPENWEATHER_BASE_URL,
            params=params,
            timeout=REQUEST_TIMEOUT
        )
        
        # Manejo de códigos de error HTTP
        if response.status_code == 401:
            return {
                'error': 'Unauthorized',
                'message': 'API key inválida o expirada',
                'status_code': 401
            }
        
        if response.status_code == 404:
            return {
                'error': 'Not Found',
                'message': 'La ciudad o ubicación no fue encontrada',
                'status_code': 404
            }
        
        if response.status_code == 429:
            return {
                'error': 'Too Many Requests',
                'message': 'Se excedió el límite de solicitudes. Intenta más tarde.',
                'status_code': 429
            }
        
        if response.status_code >= 500:
            return {
                'error': 'Server Error',
                'message': 'Error en el servidor de OpenWeather API',
                'status_code': response.status_code
            }
        
        if response.status_code != 200:
            return {
                'error': 'Error',
                'message': f'Error HTTP {response.status_code}',
                'status_code': response.status_code
            }
        
        return response.json()
        
    except requests.exceptions.Timeout:
        return {
            'error': 'Timeout',
            'message': f'La solicitud tardó más de {REQUEST_TIMEOUT} segundos',
            'status_code': 504
        }
    except requests.exceptions.ConnectionError:
        return {
            'error': 'Connection Error',
            'message': 'No se pudo conectar con OpenWeather API',
            'status_code': 503
        }
    except requests.exceptions.RequestException as e:
        return {
            'error': 'Request Error',
            'message': str(e),
            'status_code': 500
        }


def format_weather_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Formatear la respuesta de OpenWeather API a un formato limpio
    
    Args:
        data: Datos crudos de OpenWeather API
        
    Returns:
        Datos formateados de manera legible
    """
    if 'error' in data:
        return data
    
    try:
        return {
            'city': data.get('name'),
            'country': data.get('sys', {}).get('country'),
            'coordinates': {
                'lat': data.get('coord', {}).get('lat'),
                'lon': data.get('coord', {}).get('lon')
            },
            'weather': {
                'main': data.get('weather', [{}])[0].get('main'),
                'description': data.get('weather', [{}])[0].get('description'),
                'icon': data.get('weather', [{}])[0].get('icon')
            },
            'temperature': {
                'current': round(data.get('main', {}).get('temp', 0), 2), 
                'feels_like': round(data.get('main', {}).get('feels_like', 0), 2),
                'min': round(data.get('main', {}).get('temp_min', 0), 2),
                'max': round(data.get('main', {}).get('temp_max', 0), 2)
            },
            'atmospheric': {
                'pressure': data.get('main', {}).get('pressure'),
                'humidity': data.get('main', {}).get('humidity'),
                'visibility': data.get('visibility')
            },
            'wind': {
                'speed': data.get('wind', {}).get('speed'),
                'degree': data.get('wind', {}).get('deg'),
                'gust': data.get('wind', {}).get('gust')
            },
            'clouds': data.get('clouds', {}).get('all'),
            'timestamp': data.get('dt'),
            'sunrise': data.get('sys', {}).get('sunrise'),
            'sunset': data.get('sys', {}).get('sunset')
        }
    except Exception as e:
        return {
            'error': 'Formatting Error',
            'message': f'Error al formatear la respuesta: {str(e)}',
            'raw_data': data
        }


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.route('/health', methods=['GET'])
def health():
    """
    GET /health
    Verificar que el servicio está activo y disponible
    """
    is_valid, error = validate_api_key()
    
    status = {
        'status': 'healthy' if is_valid else 'unhealthy',
        'service': 'Weather API',
        'api_key_configured': is_valid
    }
    
    if error:
        status['warning'] = error['message']
    
    return jsonify(status), 200


@app.route('/', methods=['GET'])
def root():
    """
    GET /
    Información sobre la API
    """
    return jsonify({
        'name': 'Weather API',
        'version': '1.0.0',
        'description': 'API REST que consume OpenWeather API',
        'endpoints': {
            'GET /health': 'Verificar estado del servicio',
            'GET /': 'Información de la API',
            'GET /weather': 'Obtener clima por ciudad o coordenadas',
            'POST /weather/multiple': 'Obtener clima para múltiples ciudades'
        },
        'query_parameters': {
            'city': 'Nombre de la ciudad (ej: Madrid)',
            'lat': 'Latitud (ej: 40.4168)',
            'lon': 'Longitud (ej: -3.7038)'
        }
    }), 200


@app.route('/weather', methods=['GET'])
def get_weather():
    """
    GET /weather
    Obtener clima de una ciudad o por coordenadas
    
    Query parameters:
        - city: Nombre de la ciudad
        - lat & lon: Coordenadas geográficas
        
    Ejemplos:
        /weather?city=Madrid
        /weather?lat=40.4168&lon=-3.7038
    """
    # Validar API key
    is_valid, error = validate_api_key()
    if not is_valid:
        return jsonify(error), 503
    
    city = request.args.get('city', '').strip()
    lat = request.args.get('lat', '').strip()
    lon = request.args.get('lon', '').strip()
    
    # Validar parámetros
    if not city and not (lat and lon):
        return jsonify({
            'error': 'Bad Request',
            'message': 'Debes proporcionar "city" o ambos "lat" y "lon"',
            'examples': [
                '/weather?city=Madrid',
                '/weather?lat=40.4168&lon=-3.7038'
            ]
        }), 400
    
    # Validar coordenadas si se proporcionan
    if lat or lon:
        if not (lat and lon):
            return jsonify({
                'error': 'Bad Request',
                'message': 'Ambos "lat" y "lon" son requeridos'
            }), 400
        
        try:
            lat_f = float(lat)
            lon_f = float(lon)
            
            if not (-90 <= lat_f <= 90):
                return jsonify({
                    'error': 'Bad Request',
                    'message': 'La latitud debe estar entre -90 y 90'
                }), 400
            
            if not (-180 <= lon_f <= 180):
                return jsonify({
                    'error': 'Bad Request',
                    'message': 'La longitud debe estar entre -180 y 180'
                }), 400
        except ValueError:
            return jsonify({
                'error': 'Bad Request',
                'message': 'La latitud y longitud deben ser números válidos'
            }), 400
        
        params = {
            'lat': lat_f,
            'lon': lon_f,
            'appid': OPENWEATHER_API_KEY,
            'units': 'metric'
        }
    else:
        # Validar que la ciudad no esté vacía
        if len(city) < 1:
            return jsonify({
                'error': 'Bad Request',
                'message': 'El nombre de la ciudad no puede estar vacío'
            }), 400
        
        params = {
            'q': city,
            'appid': OPENWEATHER_API_KEY,
            'units': 'metric'
        }
    
    # Hacer la solicitud a OpenWeather API
    weather_data = make_weather_request(params)
    
    # Verificar si hay error
    if 'error' in weather_data:
        status_code = weather_data.get('status_code', 500)
        return jsonify(weather_data), status_code
    
    # Formatear la respuesta
    formatted_data = format_weather_response(weather_data)
    
    if 'error' in formatted_data:
        return jsonify(formatted_data), 500
    
    return jsonify({
        'success': True,
        'data': formatted_data
    }), 200


@app.route('/weather/multiple', methods=['POST'])
def get_multiple_weather():
    """
    POST /weather/multiple
    Obtener clima para múltiples ciudades
    
    Body JSON:
    {
        "cities": ["Madrid", "Barcelona", "Valencia"],
        "coordinates": [
            {"lat": 40.4168, "lon": -3.7038},
            {"lat": 41.3851, "lon": 2.1734}
        ]
    }
    """
    # Validar API key
    is_valid, error = validate_api_key()
    if not is_valid:
        return jsonify(error), 503
    
    # Obtener datos del JSON
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'error': 'Bad Request',
                'message': 'El body debe ser un JSON válido'
            }), 400
    except Exception as e:
        return jsonify({
            'error': 'Bad Request',
            'message': f'Error al parsear JSON: {str(e)}'
        }), 400
    
    cities = data.get('cities', [])
    coordinates = data.get('coordinates', [])
    
    # Validar que se proporcionó al menos una ciudad o coordenada
    if not cities and not coordinates:
        return jsonify({
            'error': 'Bad Request',
            'message': 'Debes proporcionar "cities" o "coordinates"',
            'example': {
                'cities': ['Madrid', 'Barcelona'],
                'coordinates': [
                    {'lat': 40.4168, 'lon': -3.7038},
                    {'lat': 41.3851, 'lon': 2.1734}
                ]
            }
        }), 400
    
    # Validar tipos de datos
    if cities and not isinstance(cities, list):
        return jsonify({
            'error': 'Bad Request',
            'message': '"cities" debe ser una lista de strings'
        }), 400
    
    if coordinates and not isinstance(coordinates, list):
        return jsonify({
            'error': 'Bad Request',
            'message': '"coordinates" debe ser una lista de objetos {lat, lon}'
        }), 400
    
    # Validar límite de ciudades
    total_locations = len(cities) + len(coordinates)
    if total_locations > 20:
        return jsonify({
            'error': 'Bad Request',
            'message': f'Máximo 20 ubicaciones permitidas (enviaste {total_locations})'
        }), 400
    
    results = {
        'success': True,
        'count': 0,
        'weather': [],
        'errors': []
    }
    
    # Procesar ciudades
    for city in cities:
        if not isinstance(city, str):
            results['errors'].append({
                'location': city,
                'error': 'El nombre de la ciudad debe ser un string'
            })
            continue
        
        city = city.strip()
        if not city:
            continue
        
        params = {
            'q': city,
            'appid': OPENWEATHER_API_KEY,
            'units': 'metric'
        }
        
        weather_data = make_weather_request(params)
        
        if 'error' in weather_data:
            results['errors'].append({
                'location': city,
                'error': weather_data.get('error'),
                'message': weather_data.get('message')
            })
        else:
            formatted_data = format_weather_response(weather_data)
            if 'error' not in formatted_data:
                results['weather'].append(formatted_data)
                results['count'] += 1
            else:
                results['errors'].append({
                    'location': city,
                    'error': formatted_data.get('error')
                })
    
    # Procesar coordenadas
    for coord in coordinates:
        if not isinstance(coord, dict):
            results['errors'].append({
                'location': str(coord),
                'error': 'Las coordenadas deben ser objetos con "lat" y "lon"'
            })
            continue
        
        lat = coord.get('lat')
        lon = coord.get('lon')
        
        if lat is None or lon is None:
            results['errors'].append({
                'location': str(coord),
                'error': 'Faltan "lat" o "lon" en las coordenadas'
            })
            continue
        
        try:
            lat_f = float(lat)
            lon_f = float(lon)
            
            if not (-90 <= lat_f <= 90) or not (-180 <= lon_f <= 180):
                results['errors'].append({
                    'location': f'({lat}, {lon})',
                    'error': 'Coordenadas fuera de rango válido'
                })
                continue
        except (ValueError, TypeError):
            results['errors'].append({
                'location': str(coord),
                'error': 'Latitud y longitud deben ser números'
            })
            continue
        
        params = {
            'lat': lat_f,
            'lon': lon_f,
            'appid': OPENWEATHER_API_KEY,
            'units': 'metric'
        }
        
        weather_data = make_weather_request(params)
        
        if 'error' in weather_data:
            results['errors'].append({
                'location': f'({lat}, {lon})',
                'error': weather_data.get('error'),
                'message': weather_data.get('message')
            })
        else:
            formatted_data = format_weather_response(weather_data)
            if 'error' not in formatted_data:
                results['weather'].append(formatted_data)
                results['count'] += 1
            else:
                results['errors'].append({
                    'location': f'({lat}, {lon})',
                    'error': formatted_data.get('error')
                })
    
    return jsonify(results), 200


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    """Manejar rutas no encontradas"""
    return jsonify({
        'error': 'Not Found',
        'message': 'El endpoint no existe',
        'hint': 'Visita GET / para ver los endpoints disponibles'
    }), 404


@app.errorhandler(405)
def method_not_allowed(error):
    """Manejar métodos HTTP no permitidos"""
    return jsonify({
        'error': 'Method Not Allowed',
        'message': f'El método HTTP no está permitido para este endpoint'
    }), 405


@app.errorhandler(500)
def internal_error(error):
    """Manejar errores internos del servidor"""
    return jsonify({
        'error': 'Internal Server Error',
        'message': 'Error inesperado en el servidor'
    }), 500


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False
    )
