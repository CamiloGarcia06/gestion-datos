# Limpieza de datos: Sueño ↔ Mala Salud Mental

## Variables clave
- SleepHrsNight: horas de sueño por noche
- DaysMentHlthBad: días de mala salud mental en los últimos 30

## Resumen de filas
- Filas iniciales: 10000
- Eliminadas por duplicados: 3221
- Eliminadas por faltantes en variables clave: 2294
- Filas finales para análisis: 4485

## Tratamientos aplicados
- Detección y eliminación de duplicados por `surveyyr` + `id` (si disponibles).
- Rango plausible: `sleephrsnight` en [1, 24] (0 y valores fuera de rango → NaN); `daysmenthlthbad` en [0, 30].
- Winsorización 1%-99% en `sleephrsnight`.
- Filtro de completitud: se requieren ambas variables clave no nulas.
- Normalización: z-score y min-max para ambas variables.

## Columnas potencialmente redundantes (constantes en el subset)
- Ninguna

## Correlaciones
- Pearson r: -0.153 (p=4.86e-25)
- Spearman ρ: -0.125 (p=3.85e-17)
- Interpretación: a más horas de sueño, menos días de mala salud mental; efecto débil.