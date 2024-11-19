import os
import subprocess
import sys


def main():
    if not os.path.isfile('setup.py'):
        print("Ошибка: В текущем каталоге нет файла setup.py")
        sys.exit(1)

    if os.path.isdir('dist'):
        for file in os.listdir('dist'):
            file_path = os.path.join('dist', file)
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                os.rmdir(file_path)

    try:
        subprocess.run([sys.executable, 'setup.py', 'sdist', 'bdist_wheel'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при создании пакета: {e}")
        sys.exit(1)

    try:
        subprocess.run(['twine', 'upload', '--config-file', '.pypirc', '--skip-existing', '--repository', 'pypi', 'dist/*'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при загрузке пакета: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
