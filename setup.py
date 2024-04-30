from setuptools import setup, find_packages

# READMEファイルの内容を読み込む
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="zoltraak_celsius",
    version="0.1.25",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    # package_dir={'': '.'},  # ここでベースディレクトリを指定
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Utilities",
    ],
    
    install_requires=[
        "openai",
        "anthropic",
        "groq",
        "python-dotenv",
        "pyperclip",
        "wheel",
        'art',
        'loguru',
    ],
    package_data={
        '': ['*.txt', '*.md', '*.json', '*.csv', '*.yaml', '*.yml'],
        'zoltraak': ['llms/*','utils/*', 'grimoires/**/*'],
    },
    entry_points={
        "console_scripts": [
            "zoltraak=zoltraak.cli:main",
        ],
    },
)
