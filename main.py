from flask import Flask, render_template, request, jsonify
import chess
import chess.polyglot
import random
import time
import os
import shutil

# --- Configuración de Flask y el Tablero ---
app = Flask(__name__)
# El tablero se mantiene globalmente para gestionar el estado del juego
board = chess.Board() 
# Profundidad de búsqueda global, ajustable por el usuario
PROFUNDIDAD_IA_GLOBAL = 3 

# Se intenta cargar un libro de aperturas (opcional)
# Nota: La ruta 'books/book.bin' debe existir para que esto funcione. 
# Si no tienes un libro (como 'performance.bin' o 'book.bin'), 
# el código simplemente jugará sin él.
BOOK_PATH = "books/book.bin"
OPENING_BOOK = None
try:
    if os.path.exists(BOOK_PATH):
        OPENING_BOOK = chess.polyglot.open_reader(BOOK_PATH)
except Exception as e:
    import logging
    logging.warning(f"Advertencia: No se pudo abrir el archivo '{BOOK_PATH}'. Error: {e}")


# --- Funciones de Evaluación de la IA ---

def getValueOfPiece(letter):
    """Asigna un valor a cada pieza (centipawns). Blancas (positivas) buscan maximizar, Negras (negativas) buscan minimizar."""
    # Los valores de pieza Negra (minúsculas) son NEGATIVOS
    piece_values = {
        'P': 100, # Peón blanco
        'N': 320, # Caballo blanco
        'B': 330, # Alfil blanco
        'R': 500, # Torre blanca
        'Q': 900, # Reina blanca
        'K': 20000, # Rey blanco (valor muy alto, aunque no se usa en la evaluación de material pura)
        'p': -100, # Peón negro
        'n': -320, # Caballo negro
        'b': -330, # Alfil negro
        'r': -500, # Torre negra
        'q': -900, # Reina negra
        'k': -20000 # Rey negro
    }
    return piece_values.get(letter, 0)

def evaluateBoard(boardCopy):
    """Calcula la ventaja material de la posición (Blanco vs Negro)."""
    value = 0
    # Itera sobre las 64 casillas y suma los valores de las piezas
    for i in range(64):
        piece = boardCopy.piece_at(i)
        if piece:
            value += getValueOfPiece(piece.symbol())
    
    # Podrías agregar aquí lógica para mate (si es mate, devolver +/- infinito)
    if boardCopy.is_checkmate():
        # Si es turno de la IA (Negras) y está en mate, es muy malo (valor alto para Blanco)
        if boardCopy.turn == chess.BLACK:
            return float('inf') 
        # Si es turno del usuario (Blanco) y está en mate, es muy bueno para la IA (valor bajo para Blanco)
        else:
            return -float('inf')
    
    return value

# --- Motor Minimax con Alpha-Beta Pruning ---

def minimax(boardCopy, depth, alpha, beta, maximizingPlayer):
    """Implementación de Minimax con poda Alpha-Beta."""
    if depth == 0 or boardCopy.is_game_over():
        return evaluateBoard(boardCopy)

    if maximizingPlayer: # Turno del Blanco (Busca MAXimizar)
        maxEval = -float('inf')
        for move in boardCopy.legal_moves:
            boardCopy.push(move)
            # Llama al siguiente nivel (Negras, Minimizer)
            evaluation = minimax(boardCopy, depth - 1, alpha, beta, False)
            boardCopy.pop() 
            
            maxEval = max(maxEval, evaluation)
            alpha = max(alpha, maxEval)
            if beta <= alpha:
                break
        return maxEval
    else: # Turno del Negro (Busca MINimizar)
        minEval = float('inf')
        for move in boardCopy.legal_moves:
            boardCopy.push(move)
            # Llama al siguiente nivel (Blancas, Maximizer)
            evaluation = minimax(boardCopy, depth - 1, alpha, beta, True)
            boardCopy.pop() 
            
            minEval = min(minEval, evaluation)
            beta = min(beta, minEval)
            if beta <= alpha:
                break
        return minEval

def get_ai_move(boardCopy):
    """Selecciona el mejor movimiento de la IA (Negras) utilizando el libro de aperturas o Minimax."""
    global PROFUNDIDAD_IA_GLOBAL
    
    # 1. Intentar usar el libro de aperturas
    if OPENING_BOOK:
        try:
            # Obtiene un movimiento aleatorio del libro para la posición actual
            move_from_book = OPENING_BOOK.choice(boardCopy).move
            return move_from_book.uci()
        except IndexError:
            pass # Continúa a Minimax si no hay aperturas en el libro

    # 2. Usar Minimax para buscar el mejor movimiento
    bestMove = None
    # La IA juega con negras, por lo que busca el valor MÍNIMO
    minEval = float('inf') 
    
    # Obtener y barajar los movimientos legales para evitar sesgos en el orden de búsqueda
    legal_moves_list = list(boardCopy.legal_moves)
    random.shuffle(legal_moves_list)

    for move in legal_moves_list:
        boardCopy.push(move)
        # Llama a Minimax para el siguiente turno (Blanco, Maximizer)
        # La IA evalúa la respuesta del jugador
        evaluation = minimax(boardCopy, PROFUNDIDAD_IA_GLOBAL - 1, -float('inf'), float('inf'), True)
        boardCopy.pop() 
        
        if evaluation < minEval:
            minEval = evaluation
            bestMove = move

    if bestMove:
        return bestMove.uci()
    return None

# --- Rutas de la Aplicación (Flask) ---

@app.route('/')
def index():
    """Ruta principal que sirve el tablero de ajedrez."""
    # Retorna el HTML, que necesitará estar en la carpeta 'templates/'
    return render_template('index.html')

@app.route('/reset', methods=['POST'])
def reset_game():
    """Reinicia el tablero a la posición inicial."""
    global board
    board = chess.Board()
    return jsonify({'status': 'success', 'fen': board.fen()})

@app.route('/set_difficulty', methods=['POST'])
def set_difficulty():
    """Establece la profundidad de la IA."""
    global PROFUNDIDAD_IA_GLOBAL
    try:
        data = request.json
        difficulty = int(data.get('difficulty', 3))
        # Rango seguro de dificultad para evitar búsquedas muy largas
        if 1 <= difficulty <= 5: 
            PROFUNDIDAD_IA_GLOBAL = difficulty
            return jsonify({'status': 'success', 'difficulty': PROFUNDIDAD_IA_GLOBAL})
        return jsonify({'status': 'error', 'message': 'Dificultad fuera de rango (1-5)'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/make_move', methods=['POST'])
def make_move():
    """Procesa el movimiento del usuario (Blancas) y genera el movimiento de la IA (Negras)."""
    global board
    data = request.json
    move_uci = data.get('move')
    promotion_piece = data.get('promotion', 'q') # Pieza de promoción: 'q', 'r', 'b', 'n'
    
    if not move_uci:
        return jsonify({'status': 'error', 'message': 'No se proporcionó movimiento'}), 400

    # 1. Turno del Usuario (Blancas)
    try:
        # Intenta crear el objeto Move. Si la promoción falta en 'e7e8', la añadimos si es legal.
        move = chess.Move.from_uci(move_uci)
        
        # Lógica para manejar promociones faltantes en el UCI del cliente (e7e8 en lugar de e7e8q)
        if (board.piece_at(move.from_square) == chess.Piece(chess.PAWN, chess.WHITE) and 
            chess.square_rank(move.to_square) == 7 and 
            not move.promotion):
            
            # Recrea el movimiento con la pieza de promoción
            move = chess.Move.from_uci(move_uci + promotion_piece)

        if move in board.legal_moves:
            board.push(move)
        else:
            return jsonify({'status': 'error', 'message': f'Movimiento ilegal o inválido: {move_uci}'}), 400
            
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Formato de movimiento UCI inválido'}), 400
        
    # Verifica fin de juego después del movimiento del usuario
    if board.is_game_over():
         return jsonify({
             'status': 'game_over', 
             'fen': board.fen(),
             'message': '¡Fin del juego! Resultado: ' + board.result(),
             'user_move': move_uci,
             'ai_move': None # No hay movimiento de IA si el usuario da jaque mate
         })

    # 2. Turno de la IA (Negras)
    ai_move = None
    if board.turn == chess.BLACK:
        start_time = time.time()
        
        # Pasa una copia del tablero para la búsqueda de la IA
        ai_move = get_ai_move(board.copy()) 
        
        end_time = time.time()
        print(f"La IA tardó {end_time - start_time:.2f} segundos en pensar (Profundidad: {PROFUNDIDAD_IA_GLOBAL})")
        
        if ai_move:
            board.push_uci(ai_move)
            
            # Verifica fin de juego después del movimiento de la IA
            if board.is_game_over():
                 return jsonify({
                     'status': 'game_over', 
                     'fen': board.fen(), 
                     'message': '¡Fin del juego! Resultado: ' + board.result(),
                     'user_move': move_uci,
                     'ai_move': ai_move
                 })
                 
            return jsonify({'status': 'success', 'fen': board.fen(), 'user_move': move_uci, 'ai_move': ai_move})
            
    # Si la IA no movió (ej. si el juego ya terminó), devolvemos el estado actual.
    return jsonify({'status': 'success', 'fen': board.fen(), 'user_move': move_uci, 'ai_move': None})


# --- Ejecutar el Servidor ---
if __name__ == '__main__':
    # Usamos FLASK_DEBUG para controlar el modo debug en entornos de producción.
    debug_mode = os.environ.get('FLASK_DEBUG', 'True').lower() in ('true', '1', 'yes')
    app.run(debug=debug_mode)
