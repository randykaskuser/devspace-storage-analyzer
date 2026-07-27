import PyInstaller.__main__
import os
import platform
import subprocess

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    main_script = os.path.join(current_dir, "main.py")
    
    is_mac = platform.system() == "Darwin"
    
    build_args = [
        main_script,
        '--name=DevSpace',
        '--windowed',
        '--onefile' if not is_mac else '--onedir', # macOS usually uses onedir for .app bundles
        '--clean',
        '--icon=assets/icon.ico' if not is_mac else '--icon=assets/icon.icns', # .icns for mac if they add one later, defaults otherwise
    ]
    
    # Platform-agnostic path separator for PyInstaller data
    sep = ':' if is_mac else ';'
    build_args.extend([
        f'--add-data=ui{sep}ui',
        f'--add-data=core{sep}core',
        f'--add-data=assets{sep}assets'
    ])
    
    PyInstaller.__main__.run(build_args)
    
    if is_mac:
        print("Packaging into .dmg...")
        try:
            # Requires dmgbuild (`pip install dmgbuild`)
            import dmgbuild
            app_path = os.path.join(current_dir, 'dist', 'DevSpace.app')
            dmg_path = os.path.join(current_dir, 'dist', 'DevSpace.dmg')
            if os.path.exists(app_path):
                dmgbuild.build_dmg(
                    filename=dmg_path,
                    volume_name='DevSpace',
                    settings={
                        'files': [app_path],
                        'symlinks': {'Applications': '/Applications'},
                    }
                )
                print(f"Build complete! Check the 'dist' folder for DevSpace.dmg")
            else:
                print("Error: DevSpace.app not found in dist/")
        except ImportError:
            print("dmgbuild is not installed. Please run `pip install dmgbuild` to generate the .dmg file.")
            print("The .app bundle is available in the 'dist' folder.")
    else:
        print("Build complete! Check the 'dist' folder for DevSpace.exe")
