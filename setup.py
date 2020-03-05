import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="smaland", 
    version="0.0.1",
    author="Emil Wåreus",
    author_email="emil.wareus47@gmail.com",
    description="Python Avanza API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/emilwareus/smaland",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
