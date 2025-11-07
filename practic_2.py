import csv
import sys
import os
from urllib.parse import urlparse
from urllib.request import urlopen
from urllib.error import URLError

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


def text_dependances_block(url):
    if ".git" in url:
        url = url[:-4]
    if "github.com" in url:
        url = url.replace("github.com", "raw.githubusercontent.com")
        for branch in ["main", "master"]:
            try:
                with urlopen(f"{url}/{branch}/pom.xml") as r:
                    return r.read().decode("utf-8")
            except URLError:
                continue
        raise Exception("pom.xml not found")
    else:
        with urlopen(url) as r:
            return r.read().decode("utf-8")
    


def text_beetwen_tags(text, tag):
    start_tag = f'<{tag}>'
    end_tag = f'</{tag}>'
    try:
        start = text.index(start_tag) + len(start_tag)
        end = text.index(end_tag)
        return text[start:end].strip()
    except ValueError:
        return None
    

def dependancy_args(text):
    deps = []
    start_tag = "<dependency>"
    end_tag = "</dependency>"

    i = 0
    while True:
        start = text.find(start_tag, i)
        if start == -1: break
        end = text.find(end_tag, start)
        if end == -1: break
        dep_block = text[start:end].strip()

        group = text_beetwen_tags(dep_block, "groupId")
        artifact = text_beetwen_tags(dep_block, "artifactId")
        version = text_beetwen_tags(dep_block, "version")

        if group and artifact:
            deps.append((group, artifact, version or "unknown"))
        i = end + len(end_tag)

    return deps


def check_exception():
    config_name = ''
    for i in range(7):
        config_name = 'exception' + f'{i}' + '.csv'
        config = load_config(config_name, 1)

def main():
    config = load_config('parametres.csv', 0)
    content = text_dependances_block(config["repo_url"])
    deps = dependancy_args(content)
    repo_name = config["repo_url"].split("/")[-1]
    if ".git" in repo_name:
        repo_name = repo_name[:-4]
    print(f"dependences {repo_name}:")
    for dep in deps:
        print("\t" + dep[1])


if __name__ == "__main__":
    main()
    #check_exception()