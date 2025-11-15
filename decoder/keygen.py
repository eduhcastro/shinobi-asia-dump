"""
Lógica de geração de chave por arquivo (FILE KEY) baseada em:
- s_xxteaKey (capturada via hook)
- header de 16 bytes (offset 3..18 no arquivo "tj!"/"tje"/"tjz")
"""
from typing import List

# Base key fixa (s_xxteaKey) capturada no jogo via Frida.
# Se em outro client a base mudar, basta editar esta constante.
BASE_KEY_HEX = "67 1c b6 06 83 8b 3b 78 3f 47 5b b2 a3 14 d3 1f"


def parse_hex_bytes(s: str) -> bytes:
    """Converte string tipo '67 1c b6 06 ...' em bytes."""
    parts = [p for p in s.replace(",", " ").split() if p]
    return bytes(int(p, 16) for p in parts)


def derive_file_key(base_key: bytes, header: bytes) -> bytes:
    """
    Replica o trecho relevante de lua_cocos2dx_ui_Hot_Draw_Box
    para s_xxteaKeyLen == 16.

    base_key: 16 bytes de s_xxteaKey
    header:   16 bytes de (this+3) → no arquivo: offset [3:19]
    """
    if len(base_key) != 16:
        raise ValueError(f"base_key precisa ter 16 bytes, veio {len(base_key)}")
    if len(header) != 16:
        raise ValueError(f"header precisa ter 16 bytes, veio {len(header)}")

    # v29 inicialmente zero, depois XOR 1 em todos (loop LABEL_34)
    v: List[int] = [1] * 16

    # mistura baseKey e header (loop v14)
    for i in range(16):
        v[i] ^= base_key[i] ^ header[i]

    # aplica as máscaras fixas da função Hot_Draw_Box
    masks = {
        0: 0xD6,
        1: 0x34,
        2: 0x9B,
        4: 0x40,
        5: 0xAA,
        6: 0x0D,
        7: 0x95,
        8: 0xE2,
        9: 0x48,
        10: 0xD7,
        11: 0x23,
        12: 0x8C,
        13: 0x1E,
        14: 0x69,
        15: 0xF9,
    }
    for i, m in masks.items():
        v[i] &= m

    return bytes(v)


def derive_file_key_from_file(path: str, base_key_hex: str | None = None) -> bytes:
    """
    Lê um arquivo 'tj!'/'tje'/'tjz' do disco, pega header = bytes[3:19],
    aplica a derive_file_key e retorna a FILE KEY de 16 bytes.
    """
    if base_key_hex is None:
        base_key_hex = BASE_KEY_HEX

    base_key = parse_hex_bytes(base_key_hex)

    with open(path, "rb") as f:
        data = f.read()

    header = data[3:19]
    if len(header) != 16:
        raise ValueError(f"Header muito curto: {len(header)} bytes")

    return derive_file_key(base_key, header)
