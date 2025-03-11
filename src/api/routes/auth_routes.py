"""
Rotas para autenticação e geração de tokens JWT.
"""
from flask import Blueprint, request, jsonify, current_app
import logging
from ..auth import generate_token, token_required, verify_token
from ..schemas.models import LoginSchema, TokenResponseSchema

logger = logging.getLogger(__name__)

def create_auth_blueprint(base_url="/api/auth", **options):
    """Cria um blueprint para as rotas de autenticação"""
    auth_bp = Blueprint('auth', __name__, url_prefix=base_url)
    
    login_schema = LoginSchema()
    token_schema = TokenResponseSchema()
    
    @auth_bp.route('/login', methods=['POST'])
    def login():
        """
        Endpoint para login e geração de token JWT.
        ---
        Recebe credenciais e retorna token de acesso se autenticação for bem-sucedida.
        """
        try:
            # Validar dados de entrada
            errors = login_schema.validate(request.json)
            if errors:
                return jsonify({"errors": errors}), 400
                
            data = login_schema.load(request.json)
            username = data.get('username')
            password = data.get('password')
            
            # Aqui você deve implementar a lógica real de autenticação
            # Verificando as credenciais contra seu banco de dados ou serviço
            # Por exemplo:
            
            # Exemplo simples (substituir por lógica real):
            if not authenticate_user(username, password):
                return jsonify({"message": "Credenciais inválidas"}), 401
            
            # Gerar token com dados do usuário
            user_data = get_user_data(username)  # Função que busca dados do usuário
            token = generate_token(
                user_id=user_data['id'],
                additional_data={
                    'username': username,
                    'roles': user_data.get('roles', [])
                }
            )
            
            # Opcionalmente gerar refresh token
            refresh_token = generate_token(
                user_id=user_data['id'],
                additional_data={'type': 'refresh'},
                expiry_hours=current_app.config.get('JWT_REFRESH_TOKEN_EXPIRY_HOURS', 168)
            )
            
            # Retornar tokens
            return jsonify(token_schema.dump({
                'access_token': token,
                'refresh_token': refresh_token,
                'token_type': 'bearer'
            })), 200
            
        except Exception as e:
            logger.error(f"Erro no login: {str(e)}")
            return jsonify({"message": "Erro ao processar login"}), 500
    
    @auth_bp.route('/verify', methods=['GET'])
    @token_required
    def verify():
        """
        Endpoint para verificar se token é válido.
        ---
        Requer token JWT válido. Retorna informações do usuário.
        """
        # O decorador @token_required já verificou o token
        # e adicionou o payload ao request.jwt_payload
        return jsonify({
            "valid": True,
            "user": {
                "id": request.jwt_payload.get('sub'),
                "username": request.jwt_payload.get('username'),
                "roles": request.jwt_payload.get('roles', [])
            }
        }), 200
    
    @auth_bp.route('/refresh', methods=['POST'])
    def refresh():
        """
        Endpoint para renovar token usando refresh token.
        ---
        Recebe refresh token e retorna novo token de acesso.
        """
        refresh_token = request.json.get('refresh_token')
        if not refresh_token:
            return jsonify({"message": "Refresh token não fornecido"}), 400
        
        # Verificar refresh token
        payload = verify_token(refresh_token)
        if not payload or payload.get('type') != 'refresh':
            return jsonify({"message": "Refresh token inválido"}), 401
        
        # Gerar novo token de acesso
        user_id = payload.get('sub')
        user_data = get_user_data_by_id(user_id)  # Função para buscar dados do usuário pelo ID
        
        if not user_data:
            return jsonify({"message": "Usuário não encontrado"}), 404
            
        # Gerar novo token de acesso
        new_token = generate_token(
            user_id=user_id,
            additional_data={
                'username': user_data.get('username'),
                'roles': user_data.get('roles', [])
            }
        )
        
        return jsonify(token_schema.dump({
            'access_token': new_token,
            'token_type': 'bearer'
        })), 200
    
    return auth_bp

# Funções auxiliares para autenticação (implementar conforme seu sistema)
def authenticate_user(username, password):
    """
    Função que verifica as credenciais do usuário.
    
    Esta é uma versão simplificada de exemplo.
    Em produção, deve implementar a lógica real de verificação de credenciais.
    """
    # Implementação de exemplo - substituir por sua lógica real
    # Por exemplo, verificar contra banco de dados, LDAP, etc.
    valid_credentials = {
        "admin": "senha_admin_segura",
        "usuario": "senha_usuario_segura"
    }
    
    return username in valid_credentials and valid_credentials[username] == password

def get_user_data(username):
    """
    Função que busca dados do usuário.
    
    Esta é uma versão simplificada de exemplo.
    Em produção, deve buscar dados reais do usuário no seu sistema.
    """
    # Implementação de exemplo - substituir por sua lógica real
    users = {
        "admin": {
            "id": "1",
            "username": "admin",
            "roles": ["admin", "user"]
        },
        "usuario": {
            "id": "2",
            "username": "usuario",
            "roles": ["user"]
        }
    }
    
    return users.get(username, {})

def get_user_data_by_id(user_id):
    """
    Função que busca dados do usuário pelo ID.
    
    Esta é uma versão simplificada de exemplo.
    Em produção, deve buscar dados reais do usuário no seu sistema.
    """
    # Implementação de exemplo - substituir por sua lógica real
    users_by_id = {
        "1": {
            "id": "1",
            "username": "admin",
            "roles": ["admin", "user"]
        },
        "2": {
            "id": "2",
            "username": "usuario",
            "roles": ["user"]
        }
    }
    
    return users_by_id.get(user_id) 