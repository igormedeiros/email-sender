from setuptools import setup, find_packages

setup(
    name="email_sender",
    version="0.1",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "typer>=0.9.0",
        "rich>=13.6.0",
        "python-dotenv>=1.0.0",
        "jinja2>=3.1.2",
        "pandas>=2.1.1",
        "requests",
        "beautifulsoup4",
        "flask>=2.2.0",
        "flask-cors>=4.0.0",
        "pyyaml>=6.0",
        "marshmallow>=3.19.0",  # Para validação de schemas
        "flask-limiter>=3.5.0",  # Para rate limiting
        "flask-swagger-ui>=4.11.1",  # Para documentação OpenAPI
        "PyJWT>=2.6.0",  # Para manipulação de tokens JWT
    ],
)