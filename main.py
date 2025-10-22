# PyChess AI v2.6.0 - Servidor Flask para ajedrez con IA.

from flask import Flask, render_template, request, jsonify, session
import chess
import chess.polyglot
import chess.pgn
import random
import time
import os
import uuid
import json
import socket
from datetime import datetime
from pathlib import Path
from functools import wraps
from typing import Optional, Dict, Any, Tuple, List

# Mapeo de dificultad a profundidad (Nivel directo)
DIFFICULTY_DEPTH = {
    1: 1,   # Novato
    2: 2,   # Aficionado
    3: 3,   # Intermedio
    4: 4,   # Avanzado
    5: 5    # Maestro
}

# Mapeo de niveles a ELO equivalente (para referencia)
LEVEL_ELO = {
    1: 800,    # Novato
    2: 1100,   # Aficionado
    3: 1400,   # Intermedio
    4: 1700,   # Avanzado
    5: 2000    # Maestro
}

# CONFIGURACIÓN
app = Flask(__name__)
app.secret_key = os.environ.get(
    'SECRET_KEY',
    'dev-secret-key-change-in-production'
)

# AI / search params
MAX_SEARCH_TIME = float(os.environ.get('MAX_SEARCH_TIME', 1.5))
DEFAULT_DEPTH = int(os.environ.get('DEFAULT_DEPTH', 1))
MAX_DEPTH = int(os.environ.get('MAX_DEPTH', 5))
BOOK_PATH = os.environ.get('BOOK_PATH', 'books/book.bin')
ENABLE_PGN_LOG = os.environ.get('ENABLE_PGN_LOG', '1') == '1'
PGN_FOLDER = os.environ.get('PGN_FOLDER', 'pgns')

os.makedirs(PGN_FOLDER, exist_ok=True)

# Level Configuration (simplified from ELO system)
LEVEL_MIN = 1
LEVEL_MAX = 5
LEVEL_DEFAULT = 1

def clamp_level_value(value: Any) -> int:
    """Valida y limita un valor de nivel al rango permitido (1-5)."""
    try:
        value_int = int(value)
    except (TypeError, ValueError):
        value_int = LEVEL_DEFAULT
    return max(LEVEL_MIN, min(LEVEL_MAX, value_int))


def get_depth_for_level(level: int) -> int:
    """
    Retorna la profundidad de búsqueda para un nivel dado.
    Mapeo directo: Nivel 1-5 → Profundidad 1-5
    """
    level = clamp_level_value(level)
    return DIFFICULTY_DEPTH.get(level, DEFAULT_DEPTH)


# Piece base values (centipawns)
PIECE_VALUES = {
    chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330,
    chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 20000
}

# Índices de archivos centrales (d y e) para favorecer control del centro
CENTER_FILES = {3, 4}

# Tablas posicionales (PST) - white perspective
PST = {
    chess.PAWN: [
        0, 0, 0, 0, 0, 0, 0, 0,
        50, 50, 50, 50, 50, 50, 50, 50,
        10, 10, 20, 30, 30, 20, 10, 10,
        5, 5, 10, 25, 25, 10, 5, 5,
        0, 0, 0, 20, 20, 0, 0, 0,
        5, -5, -10, 0, 0, -10, -5, 5,
        5, 10, 10, -20, -20, 10, 10, 5,
        0, 0, 0, 0, 0, 0, 0, 0
    ],
    chess.KNIGHT: [
        -50, -40, -30, -30, -30, -30, -40, -50,
        -40, -20, 0, 0, 0, 0, -20, -40,
        -30, 0, 10, 15, 15, 10, 0, -30,
        -30, 5, 15, 20, 20, 15, 5, -30,
        -30, 0, 15, 20, 20, 15, 0, -30,
        -30, 5, 10, 15, 15, 10, 5, -30,
        -40, -20, 0, 5, 5, 0, -20, -40,
        -50, -40, -30, -30, -30, -30, -40, -50
    ],
    chess.BISHOP: [
        -20, -10, -10, -10, -10, -10, -10, -20,
        -10, 0, 0, 0, 0, 0, 0, -10,
        -10, 0, 5, 10, 10, 5, 0, -10,
        -10, 5, 5, 10, 10, 5, 5, -10,
        -10, 0, 10, 10, 10, 10, 0, -10,
        -10, 10, 10, 10, 10, 10, 10, -10,
        -10, 5, 0, 0, 0, 0, 5, -10,
        -20, -10, -10, -10, -10, -10, -10, -20
    ],
    chess.ROOK: [
        0, 0, 0, 0, 0, 0, 0, 0,
        5, 10, 10, 10, 10, 10, 10, 5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        0, 0, 0, 5, 5, 0, 0, 0
    ],
    chess.QUEEN: [
        -20, -10, -10, -5, -5, -10, -10, -20,
        -10, 0, 0, 0, 0, 0, 0, -10,
        -10, 0, 5, 5, 5, 5, 0, -10,
        -5, 0, 5, 5, 5, 5, 0, -5,
        0, 0, 5, 5, 5, 5, 0, -5,
        -10, 5, 5, 5, 5, 5, 0, -10,
        -10, 0, 5, 0, 0, 0, 0, -10,
        -20, -10, -10, -5, -5, -10, -10, -20
    ],
    chess.KING: [
        -30, -40, -40, -50, -50, -40, -40, -30,
        -30, -40, -40, -50, -50, -40, -40, -30,
        -30, -40, -40, -50, -50, -40, -40, -30,
        -20, -30, -30, -40, -40, -30, -30, -20,
        -10, -20, -20, -20, -20, -20, -20, -10,
        10, 10, 0, 0, 0, 0, 10, 10,
        20, 20, 10, 0, 0, 10, 20, 20,
        20, 30, 10, 0, 0, 10, 30, 20
    ]
}

# Gestión de sesiones
game_sessions: Dict[str, Dict[str, Any]] = {}

# Libro de aperturas
OPENING_BOOK: Optional[chess.polyglot.MemoryMappedReader] = None
try:
    if os.path.exists(BOOK_PATH):
        OPENING_BOOK = chess.polyglot.open_reader(BOOK_PATH)
except (IOError, OSError):
    pass

# GESTIÓN DE SESIONES

def get_or_create_session() -> str:
    """Obtiene o crea una sesión de juego única."""
    if 'game_id' not in session:
        session['game_id'] = str(uuid.uuid4())
        game_sessions[session['game_id']] = {
            'board': chess.Board(),
            'depth': DEFAULT_DEPTH
        }
    return session['game_id']


def get_game_state() -> Dict[str, Any]:
    """Obtiene el estado del juego para la sesión actual."""
    game_id = get_or_create_session()
    if game_id not in game_sessions:
        game_sessions[game_id] = {
            'board': chess.Board(),
            'depth': DEFAULT_DEPTH
        }
    return game_sessions[game_id]


def session_required(f):
    """Decorador para asegurar sesión activa."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        get_or_create_session()
        return f(*args, **kwargs)
    return decorated_function


# SISTEMA DE GUARDADO DE PARTIDAS (Integración Pygame)

def save_game(board: chess.Board, game_config: Dict[str, Any], 
              filename: str, overwrite: bool = False) -> Tuple[bool, str]:
    """
    Guarda una partida en formato PGN + JSON metadata.
    Integración de funcionalidad de SANTIAGO HERNÁNDEZ.
    """
    try:
        if not filename.lower().endswith('.pgn'):
            filename += '.pgn'
        
        pgn_path = Path(PGN_FOLDER) / filename
        json_path = Path(PGN_FOLDER) / filename.replace('.pgn', '.json')
        
        if pgn_path.exists() and not overwrite:
            return False, f"Archivo {filename} ya existe"
        
        # Guardar PGN
        game = chess.pgn.Game.from_board(board)
        with open(pgn_path, 'w') as f:
            f.write(str(game))
        
        # Guardar metadata JSON
        metadata = {
            'vs_machine': game_config.get('vs_machine', True),
            'level': game_config.get('level', DEFAULT_DEPTH),
            'difficulty': game_config.get('difficulty', DEFAULT_DEPTH),
            'elo': game_config.get('elo', LEVEL_ELO.get(game_config.get('difficulty', DEFAULT_DEPTH), 800)),
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'filename': filename,
            'result': game_config.get('result', '*'),
            'moves_count': board.fullmove_number
        }
        with open(json_path, 'w') as f:
            json.dump(metadata, f, indent=4)
        
        print(f"💾 Partida guardada: {filename} | ELO: {metadata['elo']}")
        return True, filename
    except Exception as e:
        print(f"❌ Error guardando partida: {e}")
        return False, str(e)


def list_saved_games() -> list:
    """Lista todas las partidas guardadas."""
    pgn_path = Path(PGN_FOLDER)
    if not pgn_path.exists():
        return []
    
    games = []
    for pgn_file in pgn_path.glob('*.pgn'):
        json_file = pgn_file.with_suffix('.json')
        if json_file.exists():
            try:
                with open(json_file, 'r') as f:
                    metadata = json.load(f)
                    games.append(metadata)
            except:
                pass
    return games


def get_legal_moves_for_square(square: str) -> List[str]:
    """Retorna movimientos legales desde una casilla específica."""
    game_state = get_game_state()
    board = game_state['board']

    try:
        moves = [
            move.uci()
            for move in board.legal_moves
            if chess.square_name(move.from_square) == square
        ]
        return moves
    except ValueError:
        return []


# FUNCIONES DE EVALUACIÓN

def get_piece_value(piece: chess.Piece) -> int:
    """Retorna el valor base de una pieza en centipawns."""
    if piece is None:
        return 0
    value = PIECE_VALUES.get(piece.piece_type, 0)
    return value if piece.color == chess.WHITE else -value


def get_game_over_message(result: str) -> str:
    """Retorna un mensaje legible del resultado final."""
    if result == "1-0":
        return "♚ ¡Las Blancas ganan!"
    elif result == "0-1":
        return "♚ ¡Las Negras ganan!"
    else:
        return "🤝 ¡Tablas!"


def get_pst_value(piece: chess.Piece, square: int, board: chess.Board) -> int:
    """Retorna el valor de posición (PST) para una pieza."""
    if piece is None:
        return 0
    
    pst = PST.get(piece.piece_type)
    if pst is None:
        return 0
    
    # Convertir índice del tablero a índice PST
    # Para piezas negras, invertir el tablero
    if piece.color == chess.WHITE:
        pst_index = square
    else:
        pst_index = 63 - square
    
    value = pst[pst_index]
    return value if piece.color == chess.WHITE else -value


def evaluate_board(board_copy: chess.Board) -> float:
    """Evalúa la posición del tablero."""
    if board_copy.is_checkmate():
        return float('inf') if board_copy.turn == chess.BLACK else -float('inf')
    
    if board_copy.is_stalemate() or board_copy.is_insufficient_material():
        return 0.0
    
    evaluation = 0.0
    
    # Evaluar todas las piezas en el tablero
    for square in chess.SQUARES:
        piece = board_copy.piece_at(square)
        if piece:
            # Valor material
            evaluation += get_piece_value(piece)
            # Valor posicional
            evaluation += get_pst_value(piece, square, board_copy)
    
    return evaluation


def get_draw_context(board: chess.Board) -> Dict[str, bool]:
    """Clasifica las tablas según su causa."""
    return {
        'stalemate': board.is_stalemate(),
        'insufficient_material': board.is_insufficient_material(),
        'fifty_moves_rule': board.is_fifty_moves(),
        'threefold_repetition': board.can_claim_threefold_repetition(),
        'other_claimable_draw': board.can_claim_draw()
    }


def describe_draw_context(draw_context: Optional[Dict[str, bool]]) -> str:
    """Genera un mensaje legible a partir del contexto de tablas."""
    if not draw_context:
        return "🤝 ¡Tablas!"

    if draw_context.get('stalemate'):
        return "🤝 ¡Tablas por ahogamiento (stalemate)!"

    reasons_map = {
        'insufficient_material': 'material insuficiente',
        'fifty_moves_rule': 'regla de las 50 jugadas',
        'threefold_repetition': 'triple repetición',
        'other_claimable_draw': 'reclamación de tablas'
    }

    active_reasons = [
        label for key, label in reasons_map.items()
        if draw_context.get(key)
    ]

    if not active_reasons:
        return "🤝 ¡Tablas!"

    if len(active_reasons) == 1:
        return f"🤝 ¡Tablas por {active_reasons[0]}!"

    reasons_text = ', '.join(active_reasons[:-1]) + f" y {active_reasons[-1]}"
    return f"🤝 ¡Tablas por {reasons_text}!"


def build_game_over_payload(board: chess.Board) -> Dict[str, Any]:
    """Genera payload enriquecido con detalles del desenlace."""
    result = board.result(claim_draw=True)
    payload: Dict[str, Any] = {
        'status': 'game_over',
        'result': result,
        'message': get_game_over_message(result),
        'in_check': board.is_check(),
        'draw_context': None,
        'draw_reason': None
    }

    draw_context: Optional[Dict[str, bool]] = None

    if board.is_checkmate():
        payload['status'] = 'checkmate'
    elif board.is_stalemate():
        payload['status'] = 'stalemate'
        draw_context = get_draw_context(board)
    elif result == '1/2-1/2':
        payload['status'] = 'draw'
        draw_context = get_draw_context(board)
    elif board.can_claim_draw():
        draw_context = get_draw_context(board)

    payload['draw_context'] = draw_context

    if draw_context:
        draw_reason = describe_draw_context(draw_context)
        payload['draw_reason'] = draw_reason
        if payload['status'] in {'draw', 'stalemate'}:
            payload['message'] = draw_reason
    else:
        payload['draw_reason'] = None

    return payload


# MOTOR MINIMAX CON MEJORAS

def minimax(
    board_copy: chess.Board,
    depth: int,
    alpha: float,
    beta: float,
    maximizing: bool,
    start_time: float
) -> float:
    """Implementación de Minimax con poda Alpha-Beta y ordenación heurística."""
    if (time.time() - start_time > MAX_SEARCH_TIME or depth == 0 or board_copy.is_game_over()):
        return evaluate_board(board_copy)

    legal_moves = list(board_copy.legal_moves)

    def move_priority(move: chess.Move) -> int:
        captured_piece = board_copy.piece_at(move.to_square)
        moving_piece = board_copy.piece_at(move.from_square)
        is_capture = captured_piece is not None
        is_check = board_copy.gives_check(move)
        is_promotion = move.promotion is not None

        score = 0
        if is_capture:
            score += 10_000 + PIECE_VALUES.get(captured_piece.piece_type, 0)
            if moving_piece:
                score += 5_000 + (
                    PIECE_VALUES.get(captured_piece.piece_type, 0)
                    - PIECE_VALUES.get(moving_piece.piece_type, 0)
                )
        if is_check:
            score += 5_000
        if is_promotion:
            score += 15_000

        # Fomentar jugadas que desarrollen piezas hacia el centro
        if moving_piece and moving_piece.piece_type in {chess.KNIGHT, chess.BISHOP}:
            center_squares = {chess.D4, chess.D5, chess.E4, chess.E5}
            if move.to_square in center_squares:
                score += 2_000

        # Peones pasados avanzando
        if moving_piece and moving_piece.piece_type == chess.PAWN:
            try:
                if board_copy.is_passed_pawn(move.from_square):
                    score += 1_500
            except AttributeError:
                pass

        return score

    legal_moves.sort(key=move_priority, reverse=True)

    if maximizing:
        max_eval = -float('inf')
        for move in legal_moves:
            board_copy.push(move)
            evaluation = minimax(
                board_copy,
                depth - 1,
                alpha,
                beta,
                False,
                start_time
            )
            board_copy.pop()
            max_eval = max(max_eval, evaluation)
            alpha = max(alpha, max_eval)

            # Búsqueda de aspersión: priorizar mates
            if max_eval >= float('inf') - 1:
                break

            if beta <= alpha:
                break
        return max_eval
    else:
        min_eval = float('inf')
        for move in legal_moves:
            board_copy.push(move)
            evaluation = minimax(
                board_copy,
                depth - 1,
                alpha,
                beta,
                True,
                start_time
            )
            board_copy.pop()
            min_eval = min(min_eval, evaluation)
            beta = min(beta, min_eval)
            if beta <= alpha:
                break
        return min_eval


def get_ai_move(
    board_copy: chess.Board,
    depth: int
) -> Optional[str]:
    """Selecciona el mejor movimiento de la IA."""
    start_time = time.time()

    # Intentar libro de aperturas
    if depth <= 3 and OPENING_BOOK:
        try:
            book_move = OPENING_BOOK.choice(board_copy).move.uci()
            elapsed = time.time() - start_time
            print(
                f"📖 Movimiento del libro: {book_move} "
                f"(tiempo: {elapsed:.3f}s)"
            )
            return book_move
        except IndexError:
            pass

    # Minimax con búsqueda del mejor movimiento
    best_move = None
    max_eval = -float('inf')
    legal_moves = list(board_copy.legal_moves)

    def move_priority(move: chess.Move) -> int:
        captured_piece = board_copy.piece_at(move.to_square)
        moving_piece = board_copy.piece_at(move.from_square)
        is_capture = captured_piece is not None
        is_check = board_copy.gives_check(move)
        is_promotion = move.promotion is not None

        score = 0
        if is_capture:
            score += 10_000 + PIECE_VALUES.get(captured_piece.piece_type, 0)
            if moving_piece:
                score += 5_000 + (
                    PIECE_VALUES.get(captured_piece.piece_type, 0)
                    - PIECE_VALUES.get(moving_piece.piece_type, 0)
                )
        if is_check:
            score += 5_000
        if is_promotion:
            score += 15_000

        if moving_piece and moving_piece.piece_type in {chess.KNIGHT, chess.BISHOP}:
            center_squares = {chess.D4, chess.D5, chess.E4, chess.E5}
            if move.to_square in center_squares:
                score += 2_000

        if moving_piece and moving_piece.piece_type == chess.PAWN:
            if chess.square_file(move.to_square) in CENTER_FILES:
                score += 500

        return score

    legal_moves.sort(key=move_priority, reverse=True)

    moves_evaluated = 0
    for move in legal_moves:
        if time.time() - start_time > MAX_SEARCH_TIME:
            print(
                f"⏱️ Timeout alcanzado después de evaluar "
                f"{moves_evaluated} movimientos"
            )
            break
        board_copy.push(move)
        evaluation = minimax(
            board_copy,
            depth - 1,
            -float('inf'),
            float('inf'),
            False,
            start_time
        )
        board_copy.pop()
        if evaluation > max_eval:
            max_eval = evaluation
            best_move = move
        moves_evaluated += 1

    elapsed = time.time() - start_time
    if best_move:
        print(
            f"🤖 IA calculó: {best_move.uci()} | "
            f"Evaluación: {max_eval:.2f} | "
            f"Profundidad: {depth} | "
            f"Movimientos: {moves_evaluated} | "
            f"Tiempo: {elapsed:.2f}s"
        )

    return best_move.uci() if best_move else None


# RUTAS

@app.route('/')
@session_required
def index():
    """Ruta principal."""
    return render_template('index.html'), 200


@app.route('/reset', methods=['POST'])
@session_required
def reset_game():
    """Reinicia el tablero."""
    game_state = get_game_state()
    game_state['board'] = chess.Board()
    print("\n🔄 JUEGO REINICIADO - Nueva partida iniciada")
    return jsonify({
        'status': 'success',
        'fen': game_state['board'].fen()
    }), 200


@app.route('/set_difficulty', methods=['POST'])
@session_required
def set_difficulty():
    """Establece la dificultad de la IA con validación robusta."""
    try:
        difficulty = int(
            request.json.get('difficulty', DEFAULT_DEPTH)
        )
        if not 1 <= difficulty <= MAX_DEPTH:
            return jsonify({
                'status': 'error',
                'message': (f'Dificultad fuera de rango '
                           f'(1-{MAX_DEPTH})')
            }), 400

        game_state = get_game_state()
        game_state['difficulty'] = difficulty
        
        # Obtener nivel validado
        level = clamp_level_value(difficulty)
        
        # Obtener profundidad para el nivel
        depth = get_depth_for_level(level)
        game_state['depth'] = depth
        
        # Obtener ELO equivalente
        elo = LEVEL_ELO.get(level, 1600)
        game_state['elo'] = elo
        
        # Guardar config para historial
        game_state['level'] = level
        
        print(
            f"⚙️ DIFICULTAD CAMBIADA: Nivel {level} → Profundidad {depth} → ELO {elo}"
        )
        return jsonify({
            'status': 'success',
            'difficulty': level,
            'level': level,
            'depth': depth,
            'elo': elo
        }), 200
    except (ValueError, TypeError):
        return jsonify({
            'status': 'error',
            'message': 'Dificultad debe ser un número entero'
        }), 400


@app.route('/ai_first_move', methods=['POST'])
@session_required
def ai_first_move():
    """Genera el primer movimiento cuando el usuario juega negras."""
    try:
        game_state = get_game_state()
        board = game_state['board']
        depth = game_state['depth']

        board.reset()

        print("=" * 60)
        print("🎮 PRIMER MOVIMIENTO DE LA IA (Usuario: Negras)")
        print(f"   Profundidad configurada: {depth}")

        ai_move = get_ai_move(board.copy(), depth)

        if ai_move:
            board.push_uci(ai_move)
            print(f"✅ Primer movimiento completado: {ai_move}")
            print("=" * 60)
            return jsonify({
                'status': 'success',
                'fen': board.fen(),
                'ai_move': ai_move,
                'in_check': board.is_check()
            }), 200
        else:
            print("❌ Error: No se pudo generar movimiento")
            print("=" * 60)
            return jsonify({
                'status': 'error',
                'message': 'Error al generar movimiento'
            }), 500

    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        print("=" * 60)
        return jsonify({
            'status': 'error',
            'message': 'Error interno del servidor'
        }), 500


@app.route('/make_move', methods=['POST'])
@session_required
def make_move():
    """Procesa movimiento del usuario y genera respuesta de IA."""
    try:
        game_state = get_game_state()
        board = game_state['board']
        depth = game_state['depth']

        move_uci = request.json.get('move')
        promotion_piece = request.json.get('promotion', 'q')

        if not move_uci:
            return jsonify({
                'status': 'error',
                'message': 'No se proporcionó movimiento'
            }), 400

        print("\n" + "=" * 60)
        print(f"👤 MOVIMIENTO DEL USUARIO: {move_uci}")

        # Turno del usuario
        try:
            move = chess.Move.from_uci(move_uci)

            # Manejo de promoción
            piece_at_source = board.piece_at(move.from_square)
            if (piece_at_source and piece_at_source.piece_type == chess.PAWN):
                target_rank = chess.square_rank(move.to_square)
                if ((board.turn == chess.WHITE and target_rank == 7)
                    or (board.turn == chess.BLACK and target_rank == 0)):
                    if not move.promotion:
                        move = chess.Move.from_uci(
                            move_uci + promotion_piece
                        )
                        print(
                            f"♛ Promoción detectada: "
                            f"{move_uci} → "
                            f"{move_uci + promotion_piece}"
                        )

            if move not in board.legal_moves:
                print(f"❌ Movimiento ilegal: {move_uci}")
                print("=" * 60)
                return jsonify({
                    'status': 'error',
                    'message': f'Movimiento ilegal: {move_uci}'
                }), 400

            board.push(move)
            print("✅ Movimiento válido aplicado")

        except ValueError as e:
            print(f"❌ Error de formato: {e}")
            print("=" * 60)
            return jsonify({
                'status': 'error',
                'message': f'Formato inválido: {move_uci}'
            }), 400

        # Verificar si el juego terminó
        if board.is_game_over():
            result = board.result()
            message = get_game_over_message(result)
            print(f"🏁 JUEGO TERMINADO - Resultado: {result}")
            print("=" * 60)
            payload = build_game_over_payload(board)
            payload.update({
                'fen': board.fen(),
                'user_move': move.uci()
            })
            return jsonify(payload), 200

        # Turno de la IA
        print(f"🤖 Calculando movimiento de IA (profundidad: {depth})...")
        ai_move = get_ai_move(board.copy(), depth)

        if ai_move:
            board.push_uci(ai_move)
            print(f"✅ IA jugó: {ai_move}")

            # Verificar si la IA ganó
            if board.is_game_over():
                result = board.result()
                message = get_game_over_message(result)
                print(f"🏁 JUEGO TERMINADO - Resultado: {result}")
                print("=" * 60)
                payload = build_game_over_payload(board)
                payload.update({
                    'fen': board.fen(),
                    'user_move': move.uci(),
                    'ai_move': ai_move
                })
                return jsonify(payload), 200

            print("=" * 60)
            return jsonify({
                'status': 'success',
                'fen': board.fen(),
                'user_move': move.uci(),
                'ai_move': ai_move,
                'in_check': board.is_check()
            }), 200
        else:
            print("❌ Error: IA no pudo generar movimiento")
            print("=" * 60)
            return jsonify({
                'status': 'error',
                'message': 'Error al generar movimiento de IA'
            }), 500

    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        print("=" * 60)
        return jsonify({
            'status': 'error',
            'message': 'Error interno del servidor'
        }), 500


@app.route('/make_pvp_move', methods=['POST'])
@session_required
def make_pvp_move():
    """Procesa movimiento en modo 2 jugadores (sin IA)."""
    try:
        game_state = get_game_state()
        board = game_state['board']

        move_uci = request.json.get('move')
        promotion_piece = request.json.get('promotion', 'q')

        if not move_uci:
            return jsonify({
                'status': 'error',
                'message': 'No se proporcionó movimiento'
            }), 400

        print("\n" + "=" * 60)
        print(f"👤 MOVIMIENTO: {move_uci}")

        try:
            move = chess.Move.from_uci(move_uci)

            # Manejo de promoción
            piece_at_source = board.piece_at(move.from_square)
            if (piece_at_source and piece_at_source.piece_type == chess.PAWN):
                target_rank = chess.square_rank(move.to_square)
                if ((board.turn == chess.WHITE and target_rank == 7)
                    or (board.turn == chess.BLACK and target_rank == 0)):
                    if not move.promotion:
                        move = chess.Move.from_uci(
                            move_uci + promotion_piece
                        )
                        print(
                            f"♛ Promoción detectada: "
                            f"{move_uci} → "
                            f"{move_uci + promotion_piece}"
                        )

            if move not in board.legal_moves:
                print(f"❌ Movimiento ilegal: {move_uci}")
                print("=" * 60)
                return jsonify({
                    'status': 'error',
                    'message': f'Movimiento ilegal: {move_uci}'
                }), 400

            board.push(move)
            print("✅ Movimiento válido aplicado")

        except ValueError as e:
            print(f"❌ Error de formato: {e}")
            print("=" * 60)
            return jsonify({
                'status': 'error',
                'message': f'Formato inválido: {move_uci}'
            }), 400

        # Verificar si el juego terminó
        if board.is_game_over():
            result = board.result()
            message = get_game_over_message(result)
            print(f"🏁 JUEGO TERMINADO - Resultado: {result}")
            print("=" * 60)
            return jsonify({
                'status': 'game_over',
                'fen': board.fen(),
                'move': move.uci(),
                'message': message
            }), 200

        print("=" * 60)
        return jsonify({
            'status': 'success',
            'fen': board.fen(),
            'move': move.uci(),
            'in_check': board.is_check()
        }), 200

    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        print("=" * 60)
        return jsonify({
            'status': 'error',
            'message': 'Error interno del servidor'
        }), 500


@app.route('/get_board_state', methods=['GET'])
@session_required
def get_board_state():
    """Retorna el estado actual del tablero."""
    try:
        game_state = get_game_state()
        board = game_state['board']
        
        return jsonify({
            'status': 'success',
            'fen': board.fen(),
            'is_game_over': board.is_game_over(),
            'result': board.result() if board.is_game_over() else None,
            'is_check': board.is_check(),
            'legal_moves': [move.uci() for move in board.legal_moves]
        }), 200
    except Exception as e:
        print(f"❌ Error al obtener estado del tablero: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Error al obtener estado del tablero'
        }), 500


@app.route('/save_game', methods=['POST'])
@session_required
def save_game_endpoint():
    """Guarda la partida actual en formato PGN + JSON."""
    try:
        game_state = get_game_state()
        board = game_state['board']
        filename = request.json.get('filename', 'saved_game')
        overwrite = request.json.get('overwrite', False)
        
        game_config = {
            'vs_machine': True,
            'level': game_state.get('level', game_state.get('difficulty', DEFAULT_DEPTH)),
            'difficulty': game_state.get('difficulty', DEFAULT_DEPTH),
            'result': board.result() if board.is_game_over() else '*'
        }
        
        success, message = save_game(board, game_config, filename, overwrite)
        
        if success:
            return jsonify({
                'status': 'success',
                'filename': message,
                'message': f'Partida guardada como {message}'
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': message
            }), 400
    except Exception as e:
        print(f"❌ Error guardando partida: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/list_games', methods=['GET'])
def list_games():
    """Lista todas las partidas guardadas."""
    try:
        games = list_saved_games()
        return jsonify({
            'status': 'success',
            'games': games,
            'count': len(games)
        }), 200
    except Exception as e:
        print(f"❌ Error listando partidas: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/legal_moves', methods=['GET'])
@session_required
def get_legal_moves_endpoint():
    """Devuelve los movimientos legales desde una casilla."""
    square = request.args.get('square')
    if not square:
        return jsonify({
            'status': 'error',
            'message': 'Parámetro square requerido'
        }), 400

    moves = get_legal_moves_for_square(square)
    destinations = [move[2:4] for move in moves]
    return jsonify({
        'status': 'success',
        'from': square,
        'moves': moves,
        'destinations': destinations
    }), 200


# MAIN
if __name__ == '__main__':
    print("\n" + "="*70)
    print("🎮 PyChess AI v3.0.0 - INICIANDO SERVIDOR")
    print("   ✨ Mejoras: Sistema de Niveles simplificado (1-5)")
    print("="*70)
    print("\n📱 ACCESO LOCAL:")
    print(f"   🔗 http://127.0.0.1:5000")
    import socket
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        print(f"   🔗 http://{ip}:5000")
    except:
        print("   ⚠️  No se pudo obtener IP de red")
    print("\n⚙️ CONFIGURACIÓN:")
    print(f"   Rango de Niveles: {LEVEL_MIN}-{LEVEL_MAX}")
    print(f"   Profundidad: {DEFAULT_DEPTH} (por defecto)")
    print(f"   Tiempo máximo búsqueda: {MAX_SEARCH_TIME}s")
    print(f"   Carpeta PGN: {PGN_FOLDER}/")
    print(f"   Modo debug: ON")
    print("\n📊 MAPEO NIVEL → PROFUNDIDAD:")
    for level, depth in DIFFICULTY_DEPTH.items():
        print(f"   Nivel {level}: Profundidad {depth}")
    print("\n📋 ENDPOINTS DISPONIBLES:")
    print("   POST /make_move - Jugar contra IA")
    print("   POST /set_difficulty - Cambiar dificultad")
    print("\n" + "="*70)
    print("✅ Servidor corriendo... Presiona CTRL+C para detener\n")
    print("="*70 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
