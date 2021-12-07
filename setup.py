import setuptools


with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()


setuptools.setup(
    name="log-correlation-asgi",
    version="0.1.0",
    url="https://github.com/shaihulud/log-correlation-asgi",
    license="MIT",
    description="Log correlation middleware and filters for ASGI frameworks.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Denis Zalivin",
    author_email="zalivindenis@gmail.com",
    packages=setuptools.find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Internet :: WWW/HTTP",
        "Programming Language :: Python :: 3",
    ],
    python_requires=">=3.6",
)
