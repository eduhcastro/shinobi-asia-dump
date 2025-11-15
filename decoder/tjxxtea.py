"""
Implementação em Python do XXTEA customizado (sub_4D1DB4) + wrapper tj_xxtea_decrypt.
"""
import struct

MASK = 0xFFFFFFFF
DELTA = 0x61C88647  # 1640531527


def _u32(x: int) -> int:
    return x & MASK


def _sub_4D1DB4(data: bytes, key16: bytes) -> bytes:
    """Versão fiel do sub_4D1DB4 decompilado."""
    a2 = len(data)
    if a2 == 0:
        return b""

    # v5 = a2 >> 2; if (a2 & 3) v5++
    v50 = (a2 + 3) // 4
    v49 = 4 * v50  # tamanho em bytes arredondado
    v31 = v50 - 1

    # monta vetor de uint32 little-endian com padding de zero
    padded = data.ljust(v49, b"\x00")
    v = list(struct.unpack("<%dI" % v50, padded))

    # monta key em 4 x uint32 little-endian
    if len(key16) != 16:
        raise ValueError("key16 precisa ter 16 bytes aqui")
    k = list(struct.unpack("<4I", key16))

    # if (v50 != 1) { ... }
    if v50 != 1:
        # v33 = -1253254570 - 1640531527 * (0x34 / v50);
        v33 = _u32(-1253254570 - DELTA * (0x34 // v50))

        if v33 != 0:
            v34 = v[0]
            v51_index = v50 - 1

            while v33 != 0:
                v35 = v[v31]
                v36 = (v33 >> 2) & 3

                v37_index = v51_index
                v38 = v31
                v39_index = v51_index

                while v38 != 0:
                    v39_index -= 1
                    v40 = v[v39_index]
                    v41 = (v38 & 3) ^ v36

                    mx = (((v40 >> 5) ^ _u32(4 * v34)) +
                          ((_u32(16 * v40)) ^ (v34 >> 3))) & MASK
                    mx ^= ((k[v41] ^ v40) + (v34 ^ v33)) & MASK

                    v34 = _u32(v35 - mx)
                    v[v37_index] = v34

                    v37_index = v39_index
                    v35 = v40
                    v38 -= 1

                z = v[v31]
                mx = (((z >> 5) ^ _u32(4 * v34)) +
                      ((_u32(16 * z)) ^ (v34 >> 3))) & MASK
                mx ^= ((k[v36] ^ z) + (v34 ^ v33)) & MASK

                v34 = _u32(v[0] - mx)
                v[0] = v34

                v33 = _u32(v33 + DELTA)

    v43 = v[v31]

    if not (v43 >= v49 - 7 and v43 <= v49 - 4):
        raise ValueError(f"Tamanho decodificado inválido: v43={v43}, v49={v49}")

    full_bytes = b"".join(struct.pack("<I", x) for x in v)
    return full_bytes[:v43]


def tj_xxtea_decrypt_bytes(data: bytes, key: bytes) -> bytes:
    """Wrapper equivalente ao tj_xxtea_decrypt do jogo."""
    key_len = len(key)
    if key_len == 0:
        raise ValueError("Key vazia não é suportada.")

    if key_len > 0xF:
        key_effective = key[:16]
    else:
        key_effective = key.ljust(16, b"\x00")

    return _sub_4D1DB4(data, key_effective)
