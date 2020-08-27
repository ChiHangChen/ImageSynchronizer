from setuptools import setup

install_requires = [
    'ipython>=7.8.0',
    'opencv-python>=4.1.1.26',
    'matplotlib>=3.1.1',
    'pysmb>=1.1.28',
    'pandas>=0.25.1',
    'numpy>=1.16.5',
    'pyodbc>=4.0.27',
    'Jinja2>=2.10.3'
]

setup(
        name='ImageSynchronizer',
        version='0.4.0',
        description='ImageSynchronizer is an image dataset management project.',
        author='JimChen',
        author_email='jim71183@gmail.com',
        url='https://www.google.com.tw/',
        packages=['ImageSynchronizer'],
        install_requires=install_requires,
        include_package_data=True
)