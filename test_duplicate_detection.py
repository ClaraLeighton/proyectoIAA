#!/usr/bin/env python3
from pipeline.persistence import find_duplicate_files

# Simular subir un archivo que ya existe en el sistema
test_pending = [
    {'file_hash': '215a3dd9045f806a', 'pdf_name': 'Informe_PrePractica_Castelli.pdf'},
    {'file_hash': 'unique_hash_123', 'pdf_name': 'NuevoInforme.pdf'},
]

result = find_duplicate_files(test_pending)
print(f'Test 1: Archivo con nombre existente')
print(f'  Duplicates found: {len(result)}')
for key, dup in result.items():
    print(f'  - {dup["pdf_name"]} (Report ID: {dup["report_id"]})')

# Simular subir archivos completamente nuevos
test_pending2 = [
    {'file_hash': 'brand_new_hash_abc', 'pdf_name': 'InformeCompletamenteNuevo.pdf'},
]

result2 = find_duplicate_files(test_pending2)
print(f'\nTest 2: Archivo completamente nuevo')
print(f'  Duplicates found: {len(result2)}')

# Simular subir un archivo sin hash (edge case)
test_pending3 = [
    {'file_hash': '', 'pdf_name': 'Informe_PrePractica_Castelli.pdf'},
]

result3 = find_duplicate_files(test_pending3)
print(f'\nTest 3: Archivo sin hash pero con nombre existente')
print(f'  Duplicates found: {len(result3)}')
for key, dup in result3.items():
    print(f'  - {dup["pdf_name"]}')
