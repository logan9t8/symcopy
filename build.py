import io
import json
import requests
import subprocess
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

VERSION_PATH = 'unicode_version.txt'
DB_PATH = './data/ucd.all.flat.xml'
DS_PATH = './data/unicode_ds.json'
EXCLUDED_GC = ['Cc', 'Cf', 'Me', 'Mn', 'Zl', 'Zp']
SKIP_OTHER_LETTER = True

def init():
    # Create data directory if it doesn't exist
    Path('./data').mkdir(exist_ok=True)
    # Other letters (Lo) contains ~141k chars. While excluded, the entire DS is only ~16k chars
    if SKIP_OTHER_LETTER:
        print('Skipping other letters (Lo) in DS creation')
        EXCLUDED_GC.append('Lo')

def get_version():
    global VERSION
    try:
        with open(VERSION_PATH) as f:
            VERSION = f.read().strip()
    except FileNotFoundError:
        print(f'{VERSION_PATH} not found, aborting')
        exit(1)


def download_db() -> bool:
    # Check if DB exists and is up to date
    if Path(DB_PATH).exists():
        for event, elem in ET.iterparse(DB_PATH, events=('start',)):
            if elem.tag.endswith('description'):
                if elem.text and elem.text.split()[1] == VERSION:
                    print(f'{DB_PATH} is up to date ({VERSION})')
                    return False
                break

    # If not, download DB
    unicode_url = f'https://www.unicode.org/Public/{VERSION}/ucdxml/ucd.all.flat.zip'
    print(f'Downloading Unicode database version {VERSION}')
    response = requests.get(unicode_url, stream=True, timeout=30)
    if response.status_code != 200:
        print(f'Failed to download Unicode database')
        exit(1)
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        z.extract('ucd.all.flat.xml', path='./data')

    # Verify downloaded DB
    download_db()
    return True


def create_ds(recreate: bool):
    # Check if DS exists
    if Path(DS_PATH).exists() and not recreate:
        print(f'{DS_PATH} already exists, skipping DS creation')
        return

    # Create DS from DB
    print(f'Creating DS from {DS_PATH}')
    with open(DS_PATH, 'w', encoding='utf-8') as f:
        f.write('{\n')
        first = True
        for event, elem in ET.iterparse(DB_PATH, events=('start',)):
            if elem.tag.endswith('char'):
                na = elem.attrib.get('na')
                cp = elem.attrib.get('cp')
                gc = elem.attrib.get('gc')
                # https://www.unicode.org/reports/tr44/#General_Category_Values
                if gc and gc in EXCLUDED_GC: # Skip invisible characters
                    continue
                if na and na != '' and cp:
                    char = chr(int(cp, 16))
                    if not first:
                        f.write(',\n')
                    else:
                        first = False
                    json.dump(na.lower(), f, ensure_ascii=False)
                    f.write(': ')
                    json.dump(char, f, ensure_ascii=False)
                elem.clear()  # Clear element to save memory
        f.write('\n}\n')


def create_cli():
    # Compile rust CLI ./src/main.rs using cargo build --release
    print('Compiling Rust CLI')
    result = subprocess.run(['cargo', 'build', '--release'], capture_output=True, text=True)

    if result.returncode != 0:
        print('Failed to compile Rust CLI')
        print(result.stderr)
        exit(1)

    # Copy DS to target/release
    target_path = Path('./target/release/unicode_ds.json')
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(Path(DS_PATH).read_text(encoding='utf-8'), encoding='utf-8')
    print(f'Copied {DS_PATH} to {target_path}')

if __name__ == '__main__':
    init()
    get_version()
    recreate_ds = download_db()
    create_ds(recreate_ds)
    create_cli()
