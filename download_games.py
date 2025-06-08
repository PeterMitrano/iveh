import enum

from tqdm import tqdm
from pathlib import Path
import zipfile
import io
import requests
import bs4

@enum.unique
class FileType(enum.Enum):
    SGF = 0
    ZIP = 1



def get_urls_to_download(index_url: str):
    """
    :param index_url: URL of an index page (containing files)
    """
    games_path = Path('games')
    res = requests.get(index_url)
    data = bs4.BeautifulSoup(res.text, "html.parser")
    table = data.find('table')
    rows = table.find_all("tr")[3:-1]


    for row in rows:
        a = row.find("a")
        href = a['href']
        if 'mixed-plus-moves.sgf' == href:
            continue
        if '/' in str(href):
            yield from get_urls_to_download(index_url + href)
        else:
            file_url = index_url + href
            if '.zip' in href:
                unzipped_path = games_path / Path(href).stem
                if not unzipped_path.exists():
                    yield FileType.ZIP, file_url, unzipped_path
            elif '.sgf' in href:
                sgf_path = games_path / href
                if not sgf_path.exists():
                    yield FileType.SGF, file_url, sgf_path


def download_files(urls):
    for file_type, url, destination in tqdm(urls):
        match file_type:
            case FileType.SGF:
                res = requests.get(url, stream=True)
                with destination.open('w') as f:
                    f.write(res.text)
            case FileType.ZIP:
                res = requests.get(url, stream=True)
                z = zipfile.ZipFile(io.BytesIO(res.content))
                z.extractall(destination)
            case _:
                raise NotImplementedError()


def main():
    url = "https://www.boardspace.net/hive/hivegames/"
    urls = get_urls_to_download(url)
    download_files(urls)


if __name__ == "__main__":
    main()
