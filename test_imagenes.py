#!/usr/bin/env python3
import os
import sys

def test_busqueda_basica():
    """Test básico de búsqueda de imágenes"""
    print("🔧 TEST BÁSICO DE BÚSQUEDA")
    print("=" * 40)
    
    print(f"📍 Directorio actual: {os.getcwd()}")
    print()
    
    # Verificar assets
    if os.path.exists("assets"):
        print("✅ Carpeta 'assets' existe")
        archivos = os.listdir("assets")
        print(f"📄 Archivos en assets: {archivos}")
        
        for archivo in archivos:
            if "170" in archivo:
                print(f"🎯 Archivo con '170': {archivo}")
                ruta_completa = os.path.join("assets", archivo)
                print(f"   Ruta completa: {ruta_completa}")
                print(f"   ¿Es archivo?: {os.path.isfile(ruta_completa)}")
                print(f"   Tamaño: {os.path.getsize(ruta_completa)} bytes")
    else:
        print("❌ Carpeta 'assets' NO existe")
    
    print()
    
    # Verificar directorio actual
    archivos_actuales = os.listdir(".")
    imagenes_actuales = [f for f in archivos_actuales if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    print(f"📄 Imágenes en directorio actual: {imagenes_actuales}")
    
    for img in imagenes_actuales:
        if "170" in img:
            print(f"🎯 Imagen con '170': {img}")

if __name__ == "__main__":
    test_busqueda_basica()
