"""check the requested style of current python comments"""
from pathlib import Path
import tokenize
ROOT=Path(__file__).resolve().parents[1]

def test_python_comments_are_lowercase_without_hyphens():
    files=[ROOT/'app.py']
    for folder in ['src','scripts','tests','pages']:
        files.extend((ROOT/folder).glob('*.py'))
    for path in files:
        with tokenize.open(path) as stream:
            tokens=tokenize.generate_tokens(stream.readline)
            for token in tokens:
                if token.type==tokenize.COMMENT:
                    assert token.string==token.string.lower(),f'{path}:{token.start[0]}'
                    assert '-' not in token.string,f'{path}:{token.start[0]}'
