import PyInstaller.__main__
import os

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    main_script = os.path.join(current_dir, "main.py")
    
    PyInstaller.__main__.run([
        main_script,
        '--name=DevSpace',
        '--windowed',
        '--onefile',
        '--clean',
        '--icon=assets/icon.ico',
        '--add-data=ui;ui',
        '--add-data=core;core',
        '--add-data=assets;assets'
    ])
    
    print("Build complete! Check the 'dist' folder for DevSpace.exe")
