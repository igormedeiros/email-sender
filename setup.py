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
    ],
)