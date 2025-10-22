# PyChess AI

**Un motor de ajedrez con inteligencia artificial desarrollado en Python con Flask**

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Descripción

**PyChess AI v2.7** es un juego de ajedrez web completo que combina inteligencia artificial avanzada con una interfaz moderna e intuitiva.

> **v2.7 - Novedades**: 🔄 Sistema ELO dinámico con profundidad adaptativa | 💾 Guardado de partidas (PGN + JSON) | ✅ Validación robusta de valores ELO (200-3000)

###  ¿Qué lo hace especial?

**Motor de IA Inteligente:**
- Algoritmo **Minimax con poda Alpha-Beta** que piensa varios movimientos adelante
- **5 niveles de dificultad** ajustables en tiempo real
- Soporte para **libros de aperturas** profesionales
- Optimizado para responder en menos de 25 segundos

**Modos de Juego:**
- **vs IA**: Enfrenta a la computadora con distintas dificultades
- **2 Jugadores**: Juega con un amigo en el mismo dispositivo
- **Jugar con Negras**: Elige tu color, la IA se adapta

**Experiencia de Usuario:**
- **Alertas visuales de jaque** con animaciones
- **Pantalla de introducción** explicativa
- **Historial de movimientos** en tiempo real
- **Interfaz responsive** para móviles y tablets
- **Promoción automática** de peones

**Tecnología:**
- Backend robusto en **Flask** con arquitectura thread-safe
- Motor de ajedrez **python-chess** para validación perfecta
- Frontend interactivo con **Chessboard.js** y **jQuery**
- Sistema de sesiones para múltiples jugadores simultáneos

---

##  Demo

```bash
# Inicia el servidor
python main.py

# Abre en tu navegador
http://localhost:5000
```

## Instalación Rápida

### Requisitos Previos
- Python 3.12 o superior
- pip (gestor de paquetes de Python)

### Pasos de Instalación

```bash
# 1. Clonar el repositorio de google drive

# 2. Instalar dependencias
pip install -r requirements.txt

# 4. Ejecutar el servidor
python main.py
```

### `requirements.txt`
```txt
Flask==3.0.0
python-chess==1.999
```

---

## Estructura del Proyecto

```
PyChess-AI/
│
├── main.py                 # Servidor Flask y motor de IA
├── templates/
│   └── index.html          # Interfaz web del juego
├── books/                  # (Opcional) Libros de aperturas
│   └── book.bin
├── static/                 # (Futuro) Recursos estáticos
│   ├── css/
│   └── js/
├── requirements.txt        # Dependencias Python
├── README.md              # Este archivo
└── LICENSE                # Licencia del proyecto aunque no esta incluida
```

---

## Características

### Motor de IA ⚡ (v2.7)
- **Algoritmo Minimax** con poda Alpha-Beta
- **Evaluación avanzada** de posiciones (material + posición)
- **5 niveles de dificultad** con ELO dinámico (800-2200)
- **Profundidad adaptativa** basada en ELO (1-5 capas)
- **Validación robusta de ELO** con rango 200-3000
- **Control de timeout** (25s máximo por movimiento)
- **Soporte para libros de aperturas** (Polyglot format)

### Interfaz de Usuario
- **Arrastrar y soltar** piezas interactivo
- **Validación de movimientos** en tiempo real
- **Historial de movimientos** visible
- **Detección automática** de jaque mate, tablas y ahogado
- **Diseño responsive** para móviles y tablets
- **Reinicio de partida** con confirmación

### Funcionalidades Técnicas
- **Thread-safe** con gestión de sesiones
- **API RESTful** con códigos HTTP estándar
- **Manejo robusto** de errores
- **Type hints** completos (Python 3.12+)
- **Cumple PEP 8** y estándares modernos

---

## Cómo Funciona la IA

### Algoritmo Minimax
El motor evalúa posiciones futuras usando un árbol de búsqueda:

```python
def minimax(board, depth, alpha, beta, maximizing, start_time):
    if depth == 0 or board.is_game_over():
        return evaluate_board(board)
    
    if maximizing:  # Turno del jugador (Blancas)
        max_eval = -∞
        for move in board.legal_moves:
            eval = minimax(board, depth-1, alpha, beta, False, start_time)
            max_eval = max(max_eval, eval)
            alpha = max(alpha, eval)
            if beta <= alpha:
                break  # Poda Alpha-Beta
        return max_eval
    # ...
```

### Evaluación de Posiciones
```python
PIECE_VALUES = {
    'P': 100,  # Peón
    'N': 320,  # Caballo
    'B': 330,  # Alfil
    'R': 500,  # Torre
    'Q': 900,  # Reina
    'K': 20000 # Rey
}
```

---

## Configuración Avanzada

### Cambiar la Dificultad Predeterminada
```python
# En main.py
DEFAULT_DEPTH = 3  # Cambia a 1-5
```

### Agregar un Libro de Aperturas
```bash
# 1. Descarga un libro en formato Polyglot (.bin)
# Ejemplo: performance.bin, varied.bin, etc.

# 2. Colócalo en la carpeta books/
mkdir books
cp tu-libro.bin books/book.bin

# 3. El servidor lo cargará automáticamente
```

### Desplegar en Producción
```bash
# Usar Gunicorn (recomendado)
pip install gunicorn

# Ejecutar con 4 workers
gunicorn -w 4 -b 0.0.0.0:5000 main:app
```

---

## API Endpoints

### `GET /`
Retorna la interfaz web principal.

### `POST /make_move`
Procesa un movimiento del jugador.

**Request:**
```json
{
  "move": "e2e4",
  "promotion": "q"
}
```

**Response:**
```json
{
  "status": "success",
  "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR",
  "user_move": "e2e4",
  "ai_move": "e7e5"
}
```

### `POST /set_difficulty`
Cambia el nivel de dificultad.

**Request:**
```json
{
  "difficulty": 3
}
```

### `POST /reset`
Reinicia la partida.

**Response:**
```json
{
  "status": "success",
  "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"
}
```

### `POST /save_game` ⭐ (v2.7)
Guarda la partida actual en formato PGN con metadata JSON.

**Request:**
```json
{
  "filename": "mi_partida",
  "overwrite": false
}
```

**Response:**
```json
{
  "status": "success",
  "filename": "mi_partida.pgn",
  "message": "Partida guardada como mi_partida.pgn"
}
```

### `GET /list_games` ⭐ (v2.7)
Lista todas las partidas guardadas con metadata.

**Response:**
```json
{
  "status": "success",
  "count": 5,
  "games": [
    {
      "vs_machine": true,
      "elo": 1950,
      "difficulty": 4,
      "created_at": "2024-10-20 13:07:42",
      "filename": "mi_partida.pgn",
      "result": "1-0",
      "moves_count": 42
    }
  ]
}
```
---

## Testing

```bash
# Instalar pytest
pip install pytest

# Ejecutar tests
pytest test_main.py -v
```

### Ejemplo de Test
```python
import pytest
from main import get_piece_value, evaluate_board
import chess

def test_piece_values():
    assert get_piece_value('P') == 100
    assert get_piece_value('q') == -900

def test_initial_position():
    board = chess.Board()
    assert evaluate_board(board) == 0
```

## Novedades v2.7.0 🚀

### Mejoras de SANTIAGO HERNÁNDEZ integradas:
- ✅ **Sistema ELO avanzado**: Validación y clamping de valores (200-3000)
- ✅ **Profundidad dinámica**: Cálculo automático basado en ELO (1-5 capas)
- ✅ **Guardado de partidas**: PGN estándar + metadata JSON
- ✅ **Mejor logging**: Salida de terminal mejorada con emojis
- ✅ **API completa**: Endpoints para guardar y listar partidas

### Actualización WIP (v2.7.1)
- **Heurística central corregida**: Se introduce la constante `CENTER_FILES = {3, 4}` para favorecer control central sin depender de constantes obsoletas en `python-chess`, evitando el `AttributeError` y restableciendo el cálculo de movimientos.
- **Back-end estabilizado**: `build_game_over_payload` vuelve a producir un payload consistente para modos IA y PvP.
- **Socket local**: Las pruebas actuales limitan la URL del servidor a `127.0.0.1`, evitando exposición no deseada.

### Arquitectura mejorada:
```
PyChess AI v2.7
├── Backend robusto (Flask)
├── Motor IA (Minimax + Alpha-Beta)
├── Sistema ELO dinámico
├── Guardado de partidas (PGN)
└── Frontend responsive (Chessboard.js)
```

## Problemas Conocidos

- **Performance en profundidad 5:** Puede tardar 20-25s en posiciones complejas.
- **Libro de aperturas:** Debe estar en formato Polyglot `.bin`.
- **Mobile:** La UI es responsive pero la experiencia puede mejorarse.
- **Bloqueos en los equipos institucionales**
- **Problemas de carpetización y de Flask**
- **UI pendiente**: Falta unificar el payload de tablas en la interfaz, mejorar `startGame()` y manejar correctamente `setDifficulty`, así como resolver el texto ausente tras cerrar el modal.

**Nota**: v2.7 resuelve muchos problemas de robustez y agrega funcionalidades profesionales. La iteración v2.7.1 continúa afinando IA y comunicación con la interfaz.

### Tecnologías
- [Python](https://www.python.org/)
- [Flask](https://flask.palletsprojects.com/)
- [python-chess](https://python-chess.readthedocs.io/)
- [Chessboard.js](https://chessboardjs.com/)
- [jQuery](https://jquery.com/)


Hecho por Santiago Zuloaga Daza
