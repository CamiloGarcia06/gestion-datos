# Informe de limpieza: Conducta sexual (NHANES 2009-2012)

## Alcance
- Variables foco:
  - SexAge (edad al primer acto sexual)
  - SexNumPartnLife (número de parejas a lo largo de la vida)
  - SexNumPartYear (número de parejas en el último año)
- Archivo limpio: NHANES2009-2012_sex_clean.csv

## Decisiones de limpieza
- Valores únicos/distintos: se verificaron columnas constantes; no se eliminaron por redundancia en el subconjunto exportado.
- Valores faltantes: se mantuvieron como NaN. Para los análisis bivariados se aplica eliminación por lista (dropna) a nivel de cada par de variables.
- Atributos incorrectos/implausibles:
  - SexAge fuera de [8, 60] o mayor que Age -> NaN.
  - Conteos negativos en SexNumPartnLife o SexNumPartYear -> NaN.
- Registros atípicos: winsorización al 1 y 99 percentil en los conteos de parejas para reducir la influencia de extremos.
- Filtrado: se restringe a SexEver == True y SexAge no nulo; se exige al menos uno de los conteos de parejas no nulo.
- Normalización/transformaciones:
  - log1p en los conteos (sexnumpartnlife_log1p, sexnumpartnyear_log1p).
  - z-score de sexage (sexage_z).

## Correlaciones esperadas (lectura)
- SexAge vs SexNumPartnLife: r ~ -0.158
- SexAge vs SexNumPartnYear: r ~ -0.129

Interpretación: inicio sexual más tardío se asocia con menor número de parejas reportadas (patrón conductual/cohortes). No implica causalidad.

Nota: los coeficientes exactos se calculan al ejecutar el notebook noteebook/data_cleaning_sexual_behavior.ipynb (celda "Correlaciones").