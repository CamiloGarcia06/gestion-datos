## Gestión de Datos

Este repositorio agrupa los trabajos y notebooks de la asignatura **Gestión de Datos**.

---

## 📁 Estructura del repositorio

La colaboración se centra en notebooks compartidos dentro de la carpeta `noteebook/` (sí, con triple "e" por decisión del equipo):

```
gestion-datos/
├─ Dockerfile
├─ docker-compose.yml
├─ Makefile                ← Atajos para usuarios no familiarizados con Docker
├─ requirements.txt        ← Dependencias de análisis de datos y Jupyter
├─ noteebook/              ← Carpeta para notebooks colaborativos (.ipynb)
│   └─ .gitkeep            ← Marcador para versionado inicial
└─ README.md               ← Guía general (este archivo)
```

- **Dockerfile**: Imagen base y dependencias.
- **docker-compose.yml**: Servicio para Jupyter Lab y orquestación.
- **Makefile**: Comandos `make` para simplificar el uso de Docker.
- **requirements.txt**: Librerías de análisis de datos (NumPy, Pandas, SciPy, scikit-learn, etc.).
- **noteebook/**: Ubicación de todos los notebooks del equipo. Puedes crear subcarpetas por tema/entrega (por ejemplo, `exploracion/`, `modelado/`, `reportes/`).

---

## 🚀 Cómo entregar y organizar trabajos

1. Crea (opcional) una subcarpeta en `noteebook/` con un nombre descriptivo, por ejemplo `noteebook/exploracion_inicial/`.
2. Añade tus notebooks `.ipynb` y, si aplica, datos de ejemplo (evita datos sensibles o pesados en el repo).
3. En el README del PR describe:
   - **Objetivo** del notebook/trabajo.
   - **Pasos de ejecución** (si requiere datos externos, cómo obtenerlos).
   - **Resultados/insights** principales.
4. Trabaja en una rama nueva basada en `main` siguiendo el patrón `<nombre_del_trabajo>/<tu_usuario>`, por ejemplo:

```bash
git checkout -b exploracion_inicial/camiloGarcia
```

5. Guarda y commitea tus cambios en tu rama:

```bash
git add noteebook/
git commit -m "[ADD] exploracion_inicial: EDA sobre dataset X"
```

6. Sube tu rama al repositorio remoto:

```bash
git push origin exploracion_inicial/camiloGarcia
```

7. Abre un **Pull Request (PR)** desde tu rama hacia `main` para revisión y merge.

---

## ⚙️ Uso de Docker para aislamiento

Para evitar conflictos de librerías, el entorno de Jupyter se ejecuta en un contenedor Docker.

Ejemplo de ejecución desde la raíz del repo:

```bash
make build   # Construye imagen e inicia el servicio en segundo plano
# o bien
make up      # Inicia (si ya está construida)
```

Luego accede a Jupyter Lab en `http://localhost:8888`.

Comandos útiles:

```bash
make down     # Detiene y limpia contenedores/redes órfanas
make logs     # Sigue logs del servicio
make shell    # Abre bash dentro del contenedor
make rm       # Limpieza agresiva (imágenes no usadas) con confirmación
```

> Si agregas/actualizas librerías, puedes regenerar `requirements.txt` con `make requirements` y volver a construir con `make build`.

---

## 🛠 Buenas prácticas de Git

- **No hagas push directo** a la rama `main`.
- **Crea siempre** una rama nueva para cada trabajo/cambio (`<nombre_del_trabajo>/<tu_usuario>`).
- Trabaja y commitea tus cambios solo en tu rama.
- Abre un PR para integrar tus cambios a `main` con una descripción clara.
- Mensajes de commit sugeridos:
  - `[ADD]`: nuevo notebook o módulo.
  - `[FIX]`: corrección de errores.
  - `[IMP]`: mejoras o refactorización.
- Si renombras carpetas o ficheros, utiliza `git mv` para preservar historial.

---

## 🤝 Contribuciones y soporte

Si detectas errores o tienes sugerencias:

1. Abre un *issue* en el repositorio.
2. Propón un *pull request* siguiendo las buenas prácticas anteriores.

---

**Autor:** Juan Camilo Sandoval Garcia  
**GitHub:** @CamiloGarcia06  
**Fecha de creación:** 09 Ago 2025

