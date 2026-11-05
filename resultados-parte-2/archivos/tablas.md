# Archivos grandes: batching, buffer y paralelo

## 1. Solo I/O (calculo trivial)

| Variante | Filas | Tiempo (ms) | Memoria pico (MB) |
|---|---|---|---|
| ingenuo | 100,000 | 106.7 | 18.97 |
| lotes+buffer | 100,000 | 70.6 | 7.46 |
| ingenuo | 500,000 | 572.7 | 95.02 |
| lotes+buffer | 500,000 | 331.1 | 7.47 |
| ingenuo | 1,000,000 | 1137.3 | 190.14 |
| lotes+buffer | 1,000,000 | 740.6 | 7.47 |

## 2. I/O + calculo real (A*, grid V~2000)

| Variante | Filas | Tiempo (ms) | Memoria pico (MB) |
|---|---|---|---|
| ingenuo | 50,000 | 14058.3 | - |
| lotes+buffer | 50,000 | 13703.0 | - |
| lotes+buffer+procesos | 50,000 | 2829.1 | - |

## 3. Tamano de lote (procesos)

| Variante | Filas | Tiempo (ms) | Memoria pico (MB) |
|---|---|---|---|
| lote=10 | 50,000 | 22002.7 | 2.31 |
| lote=100 | 50,000 | 7081.3 | 2.35 |
| lote=1000 | 50,000 | 2992.9 | 2.74 |
| lote=10000 | 50,000 | 2831.2 | 7.45 |
| lote=50000 | 50,000 | 2919.7 | 18.12 |
