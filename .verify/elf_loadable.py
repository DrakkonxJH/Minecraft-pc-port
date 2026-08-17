#!/usr/bin/env python3
"""
Verifica que toda biblioteca nativa do repositorio pode ser carregada pelo
linker dinamico do Android (bionic).

Este verificador nasceu de um bug real: na tentativa de reduzir o APK, um
script removeu as secoes de depuracao dos .so e zerou os campos e_shentsize,
e_shnum e e_shstrndx do header ELF. Estruturalmente o arquivo continuava
valido -- os segmentos PT_LOAD estavam intactos, o SONAME e as dependencias
tambem --, e o verificador da epoca aprovou. Mas o bionic recusa:

    dlopen failed: "libopenal.so" has unsupported e_shentsize: 0x0
    (expected 0x40)

O bionic exige e_shentsize igual ao tamanho canonico da entrada de secao da
arquitetura (0x40 em 64 bits, 0x28 em 32 bits) INDEPENDENTEMENTE de existir
tabela de secoes. Nada nas ferramentas usuais avisa sobre isso, e o erro so
aparece quando o jogo tenta carregar a biblioteca -- no aparelho do usuario.

Referencia da checagem no bionic:
    linker/linker_phdr.cpp, ElfReader::VerifyElfHeader()
"""
import os
import struct
import sys

FAILURES = []

# Tamanho canonico da entrada da tabela de secoes, por classe de ELF
EXPECTED_SHENTSIZE = {1: 0x28, 2: 0x40}   # 1 = ELF32, 2 = ELF64
EXPECTED_PHENTSIZE = {1: 0x20, 2: 0x38}
EXPECTED_EHSIZE = {1: 0x34, 2: 0x40}

PT_LOAD = 1
PT_DYNAMIC = 2

SEARCH_ROOTS = ['app_pojavlauncher/src/main/jniLibs']


def check(cond, msg):
    if not cond:
        FAILURES.append(msg)


def verify(path):
    name = os.path.relpath(path)
    with open(path, 'rb') as fh:
        head = fh.read(64)
        size = os.path.getsize(path)

    if head[:4] != b'\x7fELF':
        FAILURES.append(f"{name}: nao comeca com o magic ELF")
        return

    ei_class = head[4]
    ei_data = head[5]
    check(ei_class in (1, 2), f"{name}: EI_CLASS invalido ({ei_class})")
    check(ei_data in (1, 2), f"{name}: EI_DATA invalido ({ei_data})")
    if ei_class not in (1, 2):
        return

    end = '<' if ei_data == 1 else '>'
    is64 = ei_class == 2

    if is64:
        e_phoff = struct.unpack_from(end + 'Q', head, 0x20)[0]
        e_shoff = struct.unpack_from(end + 'Q', head, 0x28)[0]
        e_ehsize = struct.unpack_from(end + 'H', head, 0x34)[0]
        e_phentsize = struct.unpack_from(end + 'H', head, 0x36)[0]
        e_phnum = struct.unpack_from(end + 'H', head, 0x38)[0]
        e_shentsize = struct.unpack_from(end + 'H', head, 0x3A)[0]
        e_shnum = struct.unpack_from(end + 'H', head, 0x3C)[0]
    else:
        e_phoff = struct.unpack_from(end + 'I', head, 0x1C)[0]
        e_shoff = struct.unpack_from(end + 'I', head, 0x20)[0]
        e_ehsize = struct.unpack_from(end + 'H', head, 0x28)[0]
        e_phentsize = struct.unpack_from(end + 'H', head, 0x2A)[0]
        e_phnum = struct.unpack_from(end + 'H', head, 0x2C)[0]
        e_shentsize = struct.unpack_from(end + 'H', head, 0x2E)[0]
        e_shnum = struct.unpack_from(end + 'H', head, 0x30)[0]

    # --- A checagem que motivou este arquivo -------------------------------
    # O bionic compara e_shentsize com o valor canonico SEMPRE, mesmo quando
    # e_shnum e 0. Zerar o campo "porque nao ha secoes" quebra o dlopen.
    check(e_shentsize == EXPECTED_SHENTSIZE[ei_class],
          f"{name}: e_shentsize = 0x{e_shentsize:x}, esperado "
          f"0x{EXPECTED_SHENTSIZE[ei_class]:x} -- o bionic recusaria com "
          f"'unsupported e_shentsize'")

    check(e_phentsize == EXPECTED_PHENTSIZE[ei_class],
          f"{name}: e_phentsize = 0x{e_phentsize:x}, esperado "
          f"0x{EXPECTED_PHENTSIZE[ei_class]:x}")
    check(e_ehsize == EXPECTED_EHSIZE[ei_class],
          f"{name}: e_ehsize = 0x{e_ehsize:x}, esperado "
          f"0x{EXPECTED_EHSIZE[ei_class]:x}")

    check(e_phnum > 0, f"{name}: sem program headers")
    check(e_phoff + e_phnum * e_phentsize <= size,
          f"{name}: tabela de program headers fora dos limites do arquivo")
    if e_shnum > 0:
        check(e_shoff + e_shnum * e_shentsize <= size,
              f"{name}: tabela de secoes fora dos limites do arquivo")

    # --- Segmentos carregaveis ---------------------------------------------
    with open(path, 'rb') as fh:
        fh.seek(e_phoff)
        ph = fh.read(e_phnum * e_phentsize)

    loads = 0
    has_dynamic = False
    for i in range(e_phnum):
        off = i * e_phentsize
        if off + e_phentsize > len(ph):
            break
        if is64:
            p_type = struct.unpack_from(end + 'I', ph, off)[0]
            p_offset = struct.unpack_from(end + 'Q', ph, off + 0x08)[0]
            p_filesz = struct.unpack_from(end + 'Q', ph, off + 0x20)[0]
            p_align = struct.unpack_from(end + 'Q', ph, off + 0x30)[0]
        else:
            p_type = struct.unpack_from(end + 'I', ph, off)[0]
            p_offset = struct.unpack_from(end + 'I', ph, off + 0x04)[0]
            p_filesz = struct.unpack_from(end + 'I', ph, off + 0x10)[0]
            p_align = struct.unpack_from(end + 'I', ph, off + 0x1C)[0]

        if p_type == PT_LOAD:
            loads += 1
            check(p_offset + p_filesz <= size,
                  f"{name}: PT_LOAD termina em {p_offset + p_filesz} mas o "
                  f"arquivo tem {size} bytes")
            # Android 15+ exige paginas de 16 KB em aparelhos novos; libs com
            # alinhamento de 4 KB ainda funcionam nos demais.
            check(p_align >= 4096,
                  f"{name}: PT_LOAD com alinhamento {p_align}, abaixo de 4096")
        elif p_type == PT_DYNAMIC:
            has_dynamic = True
            check(p_offset + p_filesz <= size,
                  f"{name}: PT_DYNAMIC fora dos limites do arquivo")

    check(loads > 0, f"{name}: nenhum segmento PT_LOAD")
    check(has_dynamic, f"{name}: sem PT_DYNAMIC -- nao e uma biblioteca valida")


libs = []
for root in SEARCH_ROOTS:
    for dirpath, _, files in os.walk(root):
        libs.extend(os.path.join(dirpath, f) for f in files if f.endswith('.so'))

if not libs:
    print('Nenhuma biblioteca nativa encontrada.')
    sys.exit(0)

for lib in sorted(libs):
    verify(lib)

if FAILURES:
    print("Bibliotecas que o Android recusaria carregar:")
    for f in FAILURES:
        print("  -", f)
    sys.exit(1)

print(f"{len(libs)} bibliotecas nativas conferidas, todas carregaveis")
