from setuptools import setup, find_packages

setup(
    name="math-video-agent",
    version="1.0.0",
    description="AI Agent for generating mathematical educational videos with Manim",
    packages=find_packages(),
    install_requires=[
        "Flask>=2.3.3",
        "PyPDF2>=3.0.1",
        "PyMuPDF>=1.23.5",
        "openai>=1.3.5",
        "Werkzeug>=2.3.7",
        "manim>=0.17.3",
        "requests>=2.31.0",
    ],
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Education",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)