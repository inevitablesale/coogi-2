from setuptools import setup, find_packages

setup(
    name="coogi",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "fastapi==0.104.1",
        "uvicorn[standard]==0.24.0",
        "requests==2.31.0",
        "httpx==0.24.1",
        "openai>=1.12.0",
        "pydantic==2.5.0",
        "streamlit==1.28.1",
        "supabase==2.0.0",
        "python-dotenv==1.0.0",
        "jinja2==3.1.2",
        "python-multipart==0.0.6",
    ],
    python_requires=">=3.11",
) 