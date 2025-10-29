import csv
import sys
import os
from urllib.parse import urlparse

def validate_package_name(name):
    return isinstance(name, str) and len(name.strip()) > 0

def validate_repo_url(url):
    if not isinstance(url, str) or not url.strip():
        return False

    parsed = urlparse(url)
    if parsed.scheme in ('http', 'https', 'git', 'ssh'):
        return True
    return os.path.exists(url) or os.path.isabs(url) or (url.startswith('./') or url.startswith('../'))

def validate_repo_mode(mode):
    return mode in ('clone', 'local', 'download')

def validate_tree_output(val):
    return val.lower() in ('true', 'false', '1', '0', 'yes', 'no')

def validate_max_depth(val):
    try:
        d = int(val)
        return d >= 0
    except ValueError:
        return False


def load_config(config_path, exception_test: bool):
    if not os.path.isfile(config_path):
        print(f"Ошибка: файл конфигурации '{config_path}' не найден.", file=sys.stderr)
        if not exception_test:
            sys.exit(1)
        print("\n")
        return 0

    config = {}
    expected_keys = {'package_name', 'repo_url', 'repo_mode', 'tree_output', 'max_depth'}
    validators = {
        'package_name': validate_package_name,
        'repo_url': validate_repo_url,
        'repo_mode': validate_repo_mode,
        'tree_output': validate_tree_output,
        'max_depth': validate_max_depth,
    }

    try:
        with open(config_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = row.get('parameter')
                value = row.get('value')
                if key and key in expected_keys:
                    if not validators[key](value):
                        print(f"Ошибка: недопустимое значение параметра '{key}': '{value}'", file=sys.stderr)
                        if not exception_test:
                            sys.exit(1)
                        print("\n")
                        return 0
                    config[key] = value
    except Exception as e:
        print(f"Ошибка при чтении файла конфигурации: {e}", file=sys.stderr)
        if not exception_test:
            sys.exit(1)
        print("\n")
        return 0

    missing = expected_keys - set(config.keys())
    if missing:
        print(f"Ошибка: отсутствуют обязательные параметры: {', '.join(missing)}", file=sys.stderr)
        if not exception_test:
            sys.exit(1)
        print("\n")
        return 0

    return config


def check_exception():
    config_name = ''
    for i in range(8):
        config_name = 'exception' + f'{i}' + '.csv'
        config = load_config(config_name, 1)

def main():
    config = load_config('parametres.csv', 0)

    print("Настройки приложения:")
    for key, value in config.items():
        print(f"{key}: {value}")

if __name__ == "__main__":
    main()
    #check_exception()