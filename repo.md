# Resumen del Repositorio

- **Nombre del proyecto**: PyChess AI
- **Lenguaje principal**: Python 3.13
- **Descripción breve**: Aplicación web Flask que integra un motor de ajedrez para jugar partidas contra la IA. Incluye interfaz HTML/CSS con tablero interactivo.
- **Puntos de entrada**: `main.py`
- **Dependencias clave**:
  - Flask
  - python-chess
  - gunicorn (para despliegue)
- **Estructura relevante**:
  - `main.py`: Define la app Flask, rutas y lógica de juego.
  - `templates/index.html`: Interfaz principal del tablero.
  - `static/style.css`: Estilos del tablero e interfaz.
- **Ejecutar localmente**:
  1. Instalar dependencias con `pip install -r requirements.txt` (o instalar manualmente Flask y python-chess).
  2. Ejecutar `python main.py`.
- **Puntos a considerar**:
  - Verificar soporte para Python 3.13.
  - Revisar IA de ajedrez (usa `python-chess` con un motor simple).