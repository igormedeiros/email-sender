from api.app import create_app
import logging

if __name__ == "__main__":
    # Criar e configurar a aplicação
    app = create_app()
    
    # Obter configurações de servidor do app
    host = app.config.get('SERVER_HOST', '0.0.0.0')
    port = app.config.get('SERVER_PORT', 5000)
    debug = app.config.get('DEBUG', True)
    
    # Iniciar o servidor
    print(f"⚡ Iniciando API REST em http://{host}:{port}")
    print(f"📝 Documentação disponível em http://{host}:{port}/api/docs")
    app.run(host=host, port=port, debug=debug) 