import os

import requests


def authenticate_sympla(token):
    """Verifica a autenticação do token do Sympla."""
    url = "https://api.sympla.com.br/public/v1.5.1/events"
    
    headers = {
        "s_token": token
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Levanta um erro para status 4xx e 5xx
    except requests.exceptions.HTTPError as http_err:
        raise Exception(f"Erro ao autenticar: {http_err.response.status_code} - {http_err.response.text}")
    except Exception as err:
        raise Exception(f"Erro ao autenticar: {err}")
    
    return response.status_code  

token = os.getenv('SYMPLA_TOKEN')

result = authenticate_sympla(token)
print(result)