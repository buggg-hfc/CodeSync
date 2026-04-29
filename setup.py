from setuptools import setup, find_packages

setup(
    name="codesync",
    version="0.1.0",
    description="将远程 Ubuntu 服务器代码自动同步到本地 Windows 的 GUI 工具",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "PyQt6>=6.6.0",
        "paramiko>=3.4.0",
        "cryptography>=41.0.0",
        "watchdog>=4.0.0",
        "APScheduler>=3.10.4",
        "pathspec>=0.12.1",
        "keyring>=25.0.0",
    ],
    entry_points={
        "console_scripts": [
            "codesync=codesync.main:main",
        ],
        "gui_scripts": [
            "codesyncw=codesync.main:main",  # Windows: no console window
        ],
    },
    include_package_data=True,
    package_data={
        "codesync": ["assets/*.png"],
    },
)
