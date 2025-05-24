from flask import Flask, request, render_template, redirect, url_for
import datetime
import logging

# Database and Config imports
from .config import Config
from .db_utils import (
    get_db_connection,
    create_unsubscribe_table,
    add_email_to_unsubscribe_list as db_add_email, # Alias to avoid name clash
    remove_email_from_unsubscribe_list as db_remove_email # Alias
)

app = Flask(__name__, template_folder='../../config/templates') # Adjusted template folder path
logger = logging.getLogger(__name__)

# Initialize Config and Database Table Name
try:
    config = Config()
    UNSUBSCRIBE_TABLE = config.postgres_config.get('unsubscribe_table')
    if not UNSUBSCRIBE_TABLE:
        logger.error("POSTGRES_UNSUBSCRIBE_TABLE not found in configuration. Using default 'unsubscribed_users'.")
        UNSUBSCRIBE_TABLE = 'unsubscribed_users' # Default fallback
except Exception as e:
    logger.error(f"Failed to load configuration: {e}. Using default table name 'unsubscribed_users'.")
    config = None # Ensure config is None if it fails to load
    UNSUBSCRIBE_TABLE = 'unsubscribed_users'

def init_db():
    """Initialize the database and create the unsubscribe table if it doesn't exist."""
    if not config:
        logger.error("Configuration not loaded. Skipping database initialization.")
        return
    
    conn = None
    try:
        conn = get_db_connection(config)
        if conn:
            create_unsubscribe_table(conn, UNSUBSCRIBE_TABLE)
            logger.info(f"Unsubscribe table '{UNSUBSCRIBE_TABLE}' initialization check complete.")
        else:
            logger.error("Failed to get database connection for initial table creation.")
    except Exception as e:
        logger.error(f"Error during database initialization: {e}")
    finally:
        if conn:
            conn.close()

# Call init_db() when the application starts
init_db()

# Funções auxiliares refatoradas

def add_to_unsubscribe_list(email: str) -> bool:
    """
    Adiciona um email à lista de descadastros no banco de dados.
    """
    if not email or not config:
        logger.error(f"Email or config not available. Email: {'provided' if email else 'not provided'}")
        return False
        
    email = email.lower().strip()
    conn = None
    try:
        conn = get_db_connection(config)
        if not conn:
            logger.error("Failed to get database connection for add_to_unsubscribe_list.")
            return False
        db_add_email(conn, email, UNSUBSCRIBE_TABLE) # Using the aliased function
        # Assuming db_add_email logs its own success/failure or raises exceptions
        return True
    except Exception as e:
        logger.error(f"Error adding email '{email}' to DB unsubscribe list: {e}")
        return False
    finally:
        if conn:
            conn.close()

def remove_from_unsubscribe_list(email: str) -> bool:
    """
    Remove um email da lista de descadastros no banco de dados.
    """
    if not email or not config:
        logger.error(f"Email or config not available. Email: {'provided' if email else 'not provided'}")
        return False
    
    email = email.lower().strip()
    conn = None
    try:
        conn = get_db_connection(config)
        if not conn:
            logger.error("Failed to get database connection for remove_from_unsubscribe_list.")
            return False
        db_remove_email(conn, email, UNSUBSCRIBE_TABLE) # Using the aliased function
        # Assuming db_remove_email logs its own success/failure or raises exceptions
        return True
    except Exception as e:
        logger.error(f"Error removing email '{email}' from DB unsubscribe list: {e}")
        return False
    finally:
        if conn:
            conn.close()

# Rotas

@app.route('/')
def index():
    return 'API de descadastro está funcionando. Use /unsubscribe?email=seu@email.com para descadastrar.'

@app.route('/unsubscribe')
def unsubscribe():
    """Rota para processar descadastros"""
    email = request.args.get('email')
    current_year = datetime.datetime.now().year
    
    if not email:
        return render_template(
            'error.html',
            title="Erro - Descadastro",
            heading="Ocorreu um erro",
            error_message="Email não fornecido. Por favor, use o link correto.",
            current_year=current_year
        )
    
    # Tenta adicionar o email à lista de descadastros
    success = add_to_unsubscribe_list(email) # Calls the refactored function
    
    if not success:
        return render_template(
            'error.html',
            title="Erro - Descadastro",
            heading="Ocorreu um erro",
            error_message="Não foi possível processar seu descadastro. Por favor, tente novamente.",
            current_year=current_year
        )
    
    # Gera a URL para o recadastro
    # Note: resubscribe route is currently disabled functionality-wise.
    subscribe_url = url_for('resubscribe', email=email, _external=True) 
    
    return render_template(
        'descadastro.html',
        title="Descadastro confirmado",
        heading="Descadastro Confirmado",
        email=email,
        subscribe_url=subscribe_url, # This URL will lead to the "feature unavailable" page
        current_year=current_year
    )

@app.route('/resubscribe')
def resubscribe():
    """
    Rota para processar recadastros. 
    Originalmente desativada, mas se fosse reativada, deveria chamar remove_from_unsubscribe_list.
    """
    email = request.args.get('email') # Get email if we were to use it
    current_year = datetime.datetime.now().year

    # Example if we were to re-enable (illustrative, not changing current behavior):
    # if email:
    #     success = remove_from_unsubscribe_list(email)
    #     if success:
    #         return render_template('recadastro_sucesso.html', email=email, current_year=current_year)
    #     else:
    #         return render_template('error.html', title="Erro - Recadastro", ..., current_year=current_year)
    
    return render_template(
        'error.html',
        title="Funcionalidade indisponível",
        heading="Funcionalidade indisponível",
        error_message="A funcionalidade de recadastro não está mais disponível.",
        current_year=current_year
    )

if __name__ == '__main__':
    # Setup basic logging for local development if not already configured
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("Starting Flask app for unsubscribe service (local development)...")
    app.run(host='0.0.0.0', port=5001, debug=True) # Changed port for clarity if running with main app
