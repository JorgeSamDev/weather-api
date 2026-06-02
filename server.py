#!/usr/bin/env python
"""Script para ejecutar Weather API en segundo plano"""
import os
import sys

# Cambiar al directorio del proyecto
os.chdir('/home/jsam/actividad1/actividad3/weather-api')
sys.path.insert(0, '/home/jsam/actividad1/actividad3/weather-api')

# Importar y ejecutar
from app import app

if __name__ == '__main__':
    print("=" * 50)
    print("🌤️  WEATHER API - INICIANDO")
    print("=" * 50)
    print("✅ Servidor corriendo en http://0.0.0.0:5000")
    print("✅ Presiona CTRL+C para detener")
    print("=" * 50)
    sys.stdout.flush()
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
