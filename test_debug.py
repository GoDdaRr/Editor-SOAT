#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de prueba para diagnosticar el procesamiento de SOAT
"""

import os
import sys
from main import SOATProcessor

def test_procesamiento_interno():
    """Prueba el procesamiento interno sin Flask"""
    print("=== INICIANDO PRUEBA INTERNA DE PROCESAMIENTO SOAT ===")
    
    # Crear instancia del procesador
    processor = SOATProcessor()
    
    # Mostrar imágenes disponibles
    print("\n1. MOSTRANDO IMÁGENES DISPONIBLES:")
    processor.mostrar_imagenes_disponibles_por_tipo()
    
    # Verificar que el PDF de prueba existe
    pdf_prueba = "pdf-prueba-debug.pdf"
    if not os.path.exists(pdf_prueba):
        print(f"\n❌ ERROR: No se encuentra el archivo {pdf_prueba}")
        print("Asegúrate de que el archivo esté en la carpeta principal del proyecto")
        return False
    
    print(f"\n✅ Archivo PDF encontrado: {pdf_prueba}")
    
    # Actualizar archivo PDF de Protecta con el PDF de prueba
    print("\n2. ACTUALIZANDO ARCHIVO PDF DE PROTECTA:")
    if processor.actualizar_archivo_pdf('protecta', pdf_prueba):
        print("✅ Archivo PDF actualizado correctamente")
    else:
        print("❌ Error actualizando archivo PDF")
        return False
    
    # Probar con diferentes números
    numeros_prueba = ['1', '2', '3', '12', '123']
    
    for numero in numeros_prueba:
        print(f"\n3. PROBANDO CON NÚMERO: {numero}")
        print("-" * 50)
        
        try:
            resultado = processor.procesar_soat_con_digitos(
                tipo_soat='protecta',
                numero=numero,
                archivo_salida=f"test_resultado_{numero}.jpg",
                aplicar_mejoras=True,
                factor_brillo=1.15,
                dpi_conversion=300,
                redimensionar_final=True,
                ancho_final=1694,
                alto_final=3300,
                generar_pdf=True
            )
            
            if resultado['success']:
                print(f"✅ ÉXITO para número {numero}")
                print(f"   - Dígitos procesados: {resultado.get('digitos', [])}")
                print(f"   - Imágenes pegadas: {len(resultado.get('imagenes_pegadas', []))}")
                print(f"   - Archivo generado: {resultado.get('archivo_salida', 'N/A')}")
                print(f"   - PDF generado: {resultado.get('archivo_pdf', 'N/A')}")
            else:
                print(f"❌ ERROR para número {numero}: {resultado.get('error', 'Error desconocido')}")
                
        except Exception as e:
            print(f"❌ EXCEPCIÓN para número {numero}: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
    
    print("\n=== FIN DE PRUEBA INTERNA ===")
    return True

if __name__ == "__main__":
    test_procesamiento_interno()
