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
    return mode in ('clone', 'local', 'download', 'test')

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

def get_properties(xml_content):
    props = {}
    start = xml_content.find("<properties>")
    if start == -1:
        return props
    end = xml_content.find("</properties>", start)
    if end == -1:
        return props

    props_block = xml_content[start + len("<properties>"):end].strip()

    import re
    matches = re.findall(r'<([^>]+?)>([^<]+)</\1>', props_block)
    for key, value in matches:
        props[f"${{{key}}}"] = value.strip()

    return props

def resolve_version(version, properties):
    if version and version.startswith("${") and version.endswith("}"):
        return properties.get(version, version)
    return version or "unknown"

def dependancy_args(text, properties=None):
    if properties is None:
        properties = {}

    deps = []
    start_tag = "<dependency>"
    end_tag = "</dependency>"

    i = 0
    while True:
        start = text.find(start_tag, i)
        if start == -1: break
        end = text.find(end_tag, start)
        if end == -1: break
        dep_block = text[start + len(start_tag):end].strip()

        group = text_beetwen_tags(dep_block, "groupId")
        artifact = text_beetwen_tags(dep_block, "artifactId")
        version = text_beetwen_tags(dep_block, "version")

        if group and artifact:
            resolved_version = resolve_version(version, properties)
            deps.append((group, artifact, resolved_version))
        i = end + len(end_tag)

    return deps

def build_pom_url(group_id, artifact_id, version):
    if version == "unknown":
        return None

    base = "https://repo1.maven.org/maven2"
    group_path = group_id.replace(".", "/")
    filename = f"{artifact_id}-{version}.pom"
    return f"{base}/{group_path}/{artifact_id}/{version}/{filename}"

def dfs_maven_recursive(group, artifact, version, depth, max_depth, visited, indent=""):
    if depth > max_depth:
        return

    key = f"{group}:{artifact}:{version}"
    if key in visited:
        print(f"{indent}[CYCLE] {artifact}")
        return

    visited.add(key)

    print(f"{indent}{artifact}\t{group}")

    url = build_pom_url(group, artifact, version)
    if url is None:
        return

    try:
        xml_content = text_dependances_block(url)
        properties = get_properties(xml_content)
        direct_deps = dependancy_args(xml_content, properties)

        for g, a, v in direct_deps:
            dfs_maven_recursive(g, a, v, depth + 1, max_depth, visited, indent + "    ")
    except Exception:
        pass


def main():
    config = load_config('parametres.csv', 0)
    repo_mode = config['repo_mode']
    max_depth = int(config['max_depth'])
    tree_output = config['tree_output'].lower() in ('true', '1', 'yes')


    content = text_dependances_block(config["repo_url"])
    properties = get_properties(content)
    deps = dependancy_args(content, properties)
    repo_name = config["repo_url"].split("/")[-1]
    if ".git" in repo_name:
        repo_name = repo_name[:-4]

    visited = set()
    print(repo_name)
    for g, a, v in deps:
        dfs_maven_recursive(g, a, v, 1, max_depth, visited, "    ")
    # else:
    #     visited = set()
    #     all_deps = []
    #     for g, a, v in deps:
    #         all_deps.extend(
    #             get_dependencies_recursive(g, a, v, 1, max_depth, visited)
    #         )
    #     for dep in all_deps:
    #         print(f"  {dep['depth']} {dep['artifact']}")

if __name__ == "__main__":
    main()