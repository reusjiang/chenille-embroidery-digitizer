"""Portable project paths. Build products must never overwrite a frozen release."""
from pathlib import Path
import argparse

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = 'build/bulldogs-font2-330'
SOURCE = ROOT / 'examples/bulldogs-font2/source.DST'
BASELINE = ROOT / 'releases/bulldogs-font2-330/v001'
SOURCE_SHA256 = '216b5a9f6bbce5a6285f38649230199f6bdbd7300425ba11e27e785a132bb4e7'


def output_path(value):
    out = (ROOT / value).resolve()
    # Restrict generated output to the disposable build directory.
    build = (ROOT / 'build').resolve()
    if out == build or not out.is_relative_to(build):
        raise ValueError('Output must be a subdirectory of build/. Frozen releases cannot be overwritten.')
    out.mkdir(parents=True, exist_ok=True)
    return out


def output_args(description):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--output', default=DEFAULT_OUTPUT, help='Project-relative subdirectory of build/')
    return output_path(parser.parse_args().output)
