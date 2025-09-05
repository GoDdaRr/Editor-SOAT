#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para probar la conexión con el servidor Flask
"""

import requests
import json

def test_servidor():
    """Prueba la conexión con el servidor Flask"""
    print("=== PROBANDO CONEXIÓN CON SERVIDOR FLASK ===")
    
    try:
        # Probar conexión básica
        print("1. Probando conexión básica...")
        response = requests.get("http://127.0.0.1:5000/", timeout=5)
        print(f"   Status: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('content-type', 'N/A')}")
        
        if response.status_code == 200:
            print("   ✅ Servidor respondiendo correctamente")
        else:
            print(f"   ❌ Error del servidor: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("   ❌ No se puede conectar al servidor. ¿Está ejecutándose?")
        return False
    except Exception as e:
        print(f"   ❌ Error de conexión: {str(e)}")
        return False
    
    # Probar endpoint de estado
    try:
        print("\n2. Probando endpoint de estado...")
        response = requests.get("http://127.0.0.1:5000/estado_sistema", timeout=5)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Estado del sistema: {data.get('success', False)}")
            print(f"   - PDF Protecta existe: {data.get('archivos_pdf', {}).get('protecta_existe', False)}")
            print(f"   - PDF Positiva existe: {data.get('archivos_pdf', {}).get('positiva_existe', False)}")
            print(f"   - Total imágenes: {data.get('imagenes_sistema', {}).get('total_imagenes', 0)}")
        else:
            print(f"   ❌ Error en endpoint de estado: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error probando estado: {str(e)}")
    
    # Probar endpoint de listar imágenes
    try:
        print("\n3. Probando endpoint de imágenes...")
        response = requests.get("http://127.0.0.1:5000/listar_imagenes_disponibles", timeout=5)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Imágenes disponibles: {data.get('total', 0)}")
            print(f"   - Números disponibles: {data.get('numeros_disponibles', [])}")
        else:
            print(f"   ❌ Error en endpoint de imágenes: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error probando imágenes: {str(e)}")
    
    print("\n=== FIN DE PRUEBA DE CONEXIÓN ===")
    return True

if __name__ == "__main__":
    test_servidor()
