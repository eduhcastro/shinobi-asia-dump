"""
Funções de alto nível para detectar tipo de arquivo tj!/tje/tjz
e decodificar em disco.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from .keygen import derive_file_key_from_file
from .tjxxtea import tj_xxtea_decrypt_bytes

TjType = Literal["tj_bang", "tje", "tjz", "unknown"]


def detect_tj_type(path: str | Path) -> TjType:
    p = Path(path)
    try:
        with p.open("rb") as f:
            magic = f.read(3)
    except OSError:
        return "unknown"

    if magic == b"tj!":
        return "tj_bang"
    if magic == b"tje":
        return "tje"
    if magic == b"tjz":
        return "tjz"
    return "unknown"


def default_output_path(src: Path) -> Path:
    """Gera um caminho de saída amigável: foo.bar -> foo.dec.bar"""
    if src.suffix:
        return src.with_name(f"{src.stem}.dec{src.suffix}")
    return src.with_name(src.name + ".dec")


def decode_single_file(path: str | Path,
                       out_path: str | Path | None = None,
                       base_key_hex: str | None = None,
                       header_size: int = 23) -> Path:
    """Decodifica um único arquivo tj!/tje/tjz.

    Retorna o Path do arquivo de saída.
    """
    src = Path(path)
    if out_path is None:
        out_path = default_output_path(src)
    dst = Path(out_path)

    with src.open("rb") as f:
        raw = f.read()

    magic = raw[:3]
    if magic not in (b"tj!", b"tje", b"tjz"):
        raise ValueError(f"Arquivo {src} não parece ser tj!/tje/tjz (magic={magic!r})")

    # header usado pelo jogo = this+3 → no arquivo é offset 3..18
    header = raw[3:19]
    if len(header) != 16:
        raise ValueError(f"Header muito curto em {src}: {len(header)} bytes")

    key_bytes = derive_file_key_from_file(str(src), base_key_hex)
    data_for_xxtea = raw[header_size:]
    decrypted = tj_xxtea_decrypt_bytes(data_for_xxtea, key_bytes)

    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("wb") as f:
        f.write(decrypted)

    return dst


def iter_tj_files(root: str | Path,
                  include_tj_bang: bool = True,
                  include_tje: bool = True,
                  include_tjz: bool = False):
    """Itera recursivamente arquivos que começam com tj!/tje/tjz."""
    root_path = Path(root)
    for dirpath, _, filenames in os.walk(root_path):
        for name in filenames:
            full = Path(dirpath) / name
            t = detect_tj_type(full)
            if t == "tj_bang" and include_tj_bang:
                yield full, t
            elif t == "tje" and include_tje:
                yield full, t
            elif t == "tjz" and include_tjz:
                yield full, t
