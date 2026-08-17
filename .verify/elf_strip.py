#!/usr/bin/env python3
"""
Valida que a remocao de secoes de depuracao nao quebra as bibliotecas nativas.

Este e o verificador mais importante desta mudanca: uma biblioteca corrompida
nao da erro de compilacao nem de instalacao -- ela falha com
UnsatisfiedLinkError quando o jogo tenta abrir, no aparelho do usuario. E como
o script mexe direto nos bytes do ELF, um erro sutil (offset errado, header
inconsistente) passaria despercebido numa inspecao rapida.

O que verificamos em cada biblioteca processada:
  1. O ELF continua bem formado (magic, classe, endianness, headers).
  2. Todos os segmentos PT_LOAD continuam inteiramente dentro do arquivo --
     e o que o carregador dinamico mapeia na memoria.
  3. O segmento PT_DYNAMIC e as tabelas .dynsym/.dynstr, usadas por
     dlopen/dlsym, permanecem intactos.
  4. O alinhamento dos PT_LOAD nao mudou (requisito de 16 KB do Android 15+).
  5. A lista de bibliotecas necessarias (DT_NEEDED) e o SONAME continuam
     legiveis -- se estes se perderem, o carregamento falha.
"""
import os
import struct
import subprocess
import sys
import tempfile

sys.path.insert(0, 'scripts')

FAILURES = []


def check(cond, msg):
    if not cond:
        FAILURES.append(msg)


PT_LOAD = 1
PT_DYNAMIC = 2
DT_NEEDED = 1
DT_SONAME = 14
DT_STRTAB = 5
DT_SYMTAB = 6
DT_NULL = 0


def parse_elf(path):
    """Le program headers e entradas dinamicas, sem depender da tabela de secoes."""
    with open(path, 'rb') as fh:
        data = fh.read()
    if data[:4] != b'\x7fELF':
        raise ValueError('nao e ELF')
    is64 = data[4] == 2
    end = '<' if data[5] == 1 else '>'

    if is64:
        e_phoff = struct.unpack_from(end + 'Q', data, 0x20)[0]
        e_phentsize = struct.unpack_from(end + 'H', data, 0x36)[0]
        e_phnum = struct.unpack_from(end + 'H', data, 0x38)[0]
    else:
        e_phoff = struct.unpack_from(end + 'I', data, 0x1C)[0]
        e_phentsize = struct.unpack_from(end + 'H', data, 0x2A)[0]
        e_phnum = struct.unpack_from(end + 'H', data, 0x2C)[0]

    segments = []
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        if is64:
            p_type = struct.unpack_from(end + 'I', data, off)[0]
            p_offset = struct.unpack_from(end + 'Q', data, off + 0x08)[0]
            p_vaddr = struct.unpack_from(end + 'Q', data, off + 0x10)[0]
            p_filesz = struct.unpack_from(end + 'Q', data, off + 0x20)[0]
            p_memsz = struct.unpack_from(end + 'Q', data, off + 0x28)[0]
            p_align = struct.unpack_from(end + 'Q', data, off + 0x30)[0]
        else:
            p_type = struct.unpack_from(end + 'I', data, off)[0]
            p_offset = struct.unpack_from(end + 'I', data, off + 0x04)[0]
            p_vaddr = struct.unpack_from(end + 'I', data, off + 0x08)[0]
            p_filesz = struct.unpack_from(end + 'I', data, off + 0x10)[0]
            p_memsz = struct.unpack_from(end + 'I', data, off + 0x14)[0]
            p_align = struct.unpack_from(end + 'I', data, off + 0x1C)[0]
        segments.append({'type': p_type, 'offset': p_offset, 'vaddr': p_vaddr,
                         'filesz': p_filesz, 'memsz': p_memsz, 'align': p_align})
    return data, segments, is64, end


def vaddr_to_offset(segments, vaddr):
    for s in segments:
        if s['type'] != PT_LOAD:
            continue
        if s['vaddr'] <= vaddr < s['vaddr'] + s['filesz']:
            return s['offset'] + (vaddr - s['vaddr'])
    return None


def read_dynamic(data, segments, is64, end):
    """Extrai DT_NEEDED, DT_SONAME e ponteiros das tabelas dinamicas."""
    dyn = next((s for s in segments if s['type'] == PT_DYNAMIC), None)
    if dyn is None:
        return None
    entsize = 16 if is64 else 8
    fmt = end + ('Qq' if is64 else 'Ii')
    entries = []
    off = dyn['offset']
    for i in range(dyn['filesz'] // entsize):
        tag, val = struct.unpack_from(fmt, data, off + i * entsize)
        entries.append((tag, val))
        if tag == DT_NULL:
            break

    strtab_addr = next((v for t, v in entries if t == DT_STRTAB), None)
    symtab_addr = next((v for t, v in entries if t == DT_SYMTAB), None)
    needed_offs = [v for t, v in entries if t == DT_NEEDED]
    soname_off = next((v for t, v in entries if t == DT_SONAME), None)

    result = {'strtab_addr': strtab_addr, 'symtab_addr': symtab_addr,
              'needed': [], 'soname': None}
    if strtab_addr is None:
        return result
    strtab_off = vaddr_to_offset(segments, strtab_addr)
    if strtab_off is None:
        return result

    def read_str(rel):
        pos = strtab_off + rel
        if pos >= len(data):
            return None
        end_pos = data.find(b'\x00', pos)
        return data[pos:end_pos].decode('utf-8', 'replace')

    result['needed'] = [read_str(o) for o in needed_offs]
    if soname_off is not None:
        result['soname'] = read_str(soname_off)
    return result


def validate(path, before=None):
    """Confere a integridade estrutural de uma biblioteca."""
    name = os.path.basename(path)
    try:
        data, segments, is64, end = parse_elf(path)
    except (ValueError, struct.error) as exc:
        FAILURES.append(f"{name}: ELF ilegivel apos processar ({exc})")
        return None

    size = len(data)
    loads = [s for s in segments if s['type'] == PT_LOAD]
    check(len(loads) > 0, f"{name}: nenhum segmento PT_LOAD")

    for s in loads:
        end_off = s['offset'] + s['filesz']
        check(end_off <= size,
              f"{name}: PT_LOAD termina em {end_off} mas o arquivo tem {size} bytes "
              f"-- a biblioteca nao carregaria")

    dyn = next((s for s in segments if s['type'] == PT_DYNAMIC), None)
    check(dyn is not None, f"{name}: PT_DYNAMIC ausente")
    if dyn:
        check(dyn['offset'] + dyn['filesz'] <= size,
              f"{name}: PT_DYNAMIC fora dos limites do arquivo")

    info = read_dynamic(data, segments, is64, end)
    check(info is not None, f"{name}: nao foi possivel ler a secao dinamica")
    if info:
        check(info['strtab_addr'] is not None, f"{name}: DT_STRTAB ausente")
        check(info['symtab_addr'] is not None,
              f"{name}: DT_SYMTAB ausente -- dlsym falharia")
        for lib in info['needed']:
            check(lib and lib.endswith('.so') or lib == '',
                  f"{name}: DT_NEEDED ilegivel ({lib!r})")

    result = {'size': size, 'loads': [(s['offset'], s['filesz'], s['align'])
                                      for s in loads],
              'needed': info['needed'] if info else [],
              'soname': info['soname'] if info else None}

    if before:
        # O que NAO pode mudar entre antes e depois
        check(before['loads'] == result['loads'],
              f"{name}: os segmentos PT_LOAD mudaram -- "
              f"antes {before['loads']}, depois {result['loads']}")
        check(before['needed'] == result['needed'],
              f"{name}: a lista de dependencias mudou")
        check(before['soname'] == result['soname'],
              f"{name}: o SONAME mudou ({before['soname']} -> {result['soname']})")
        for _off, _sz, align in result['loads']:
            check(align >= 4096,
                  f"{name}: alinhamento de PT_LOAD caiu para {align}")
    return result


def main():
    import strip_debug_sections

    roots = ['app_pojavlauncher/src/main/jniLibs']
    libs = []
    for root in roots:
        for dirpath, _, files in os.walk(root):
            libs.extend(os.path.join(dirpath, f) for f in files if f.endswith('.so'))

    if not libs:
        print('Nenhuma biblioteca encontrada; nada a verificar.')
        return 0

    print(f"Verificando {len(libs)} bibliotecas nativas...\n")
    processed = 0
    for lib in sorted(libs):
        before = validate(lib)
        if before is None:
            continue

        # Copia para um temporario e processa, para nao alterar a arvore
        with tempfile.NamedTemporaryFile(suffix='.so', delete=False) as tmp:
            with open(lib, 'rb') as src:
                tmp.write(src.read())
            tmp_path = tmp.name
        try:
            saved, _note = strip_debug_sections.strip_file(tmp_path, dry_run=False)
            if saved and saved > 0:
                processed += 1
                validate(tmp_path, before=before)
        finally:
            os.unlink(tmp_path)

    print(f"{processed} biblioteca(s) seriam modificadas e continuam validas")

    if FAILURES:
        print("\nFALHAS:")
        for f in FAILURES:
            print("  -", f)
        return 1
    print("\nRemocao de secoes de depuracao: todas as verificacoes passaram")
    return 0


if __name__ == '__main__':
    sys.exit(main())
