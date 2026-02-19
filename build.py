# build.py
import PyInstaller.__main__

PyInstaller.__main__.run([
    'main.py',
    '--name=SCUMLootTools',  # Name of the executable
    '--onefile',             # Create a single executable file
    '--windowed',            # Hide the console window
])