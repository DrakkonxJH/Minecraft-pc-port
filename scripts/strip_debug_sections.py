#!/usr/bin/env python3
"""
Remove secoes de depuracao (.debug_*, .symtab, .strtab) de bibliotecas ELF.

Por que nao usar `strip`/`objcopy`: o binutils do host so reconhece o ELF da
propria arquitetura, e estas bibliotecas sao ARM64/ARM32/x86. O `llvm-strip`
do NDK resolveria, mas exige o NDK instalado. Este script trabalha direto na
estrutura do arquivo, entao roda em qualquer maquina com Python.

O que ele faz, e por que e seguro:
  - Remove apenas secoes NAO alocadas (sem a flag SHF_ALLOC). Essas secoes nao
    sao carregadas na memoria em tempo de execucao -- existem so para
    depuradores. O carregador dinamico do Android usa os segmentos PT_LOAD, que
    ficam intactos.
  - Preserva .dynsym/.dynstr (tabela de simbolos DINAMICA), que e o que o
    dlopen/dlsym usam. Remover essas quebraria o carregamento.
  - Nao altera program headers nem o layout dos segmentos carregaveis, portanto
    o alinhamento de pagina (importante para o requisito de 16 KB do Android
    15+) permanece exatamente como estava.

Uso:
    python3 scripts/strip_debug_sections.py <arquivo.so | diretorio> [...]
    python3 scripts/strip_debug_sections.py --dry-run <caminho>
"""
import os
import struct
import sys

# Secoes que removemos quando NAO forem alocadas
STRIP_PREFIXES = ('.debug_', '.zdebug_', '.gnu.debuglink', '.comment',
                  '.note.gnu.gold-version')
STRIP_EXACT = {'.symtab', '.strtab', '.stab', '.stabstr'}

# Nunca remover: usadas em tempo de execucao pelo linker dinamico
NEVER_STRIP = {'.dynsym', '.dynstr', '.dynamic', '.hash', '.gnu.hash',
               '.rela.dyn', '.rela.plt', '.rel.dyn', '.rel.plt',
               '.gnu.version', '.gnu.version_r', '.gnu.version_d',
               '.init_array', '.fini_array', '.text', '.data', '.rodata',
               '.bss', '.got', '.plt', '.eh_frame', '.eh_frame_hdr',
               '.note.android.ident'}

SHF_ALLOC = 0x2


class ElfError(Exception):
    pass


def _read_elf(path):
    with open(path, 'rb') as fh:
        data = bytearray(fh.read())
    if data[:4] != b'\x7fELF':
        raise ElfError('nao e um ELF')
    is64 = data[4] == 2
    little = data[5] == 1
    end = '<' if little else '>'

    if is64:
        e_shoff = struct.unpack_from(end + 'Q', data, 0x28)[0]
        e_shentsize = struct.unpack_from(end + 'H', data, 0x3A)[0]
        e_shnum = struct.unpack_from(end + 'H', data, 0x3C)[0]
        e_shstrndx = struct.unpack_from(end + 'H', data, 0x3E)[0]
    else:
        e_shoff = struct.unpack_from(end + 'I', data, 0x20)[0]
        e_shentsize = struct.unpack_from(end + 'H', data, 0x2E)[0]
        e_shnum = struct.unpack_from(end + 'H', data, 0x30)[0]
        e_shstrndx = struct.unpack_from(end + 'H', data, 0x32)[0]

    if e_shoff == 0 or e_shnum == 0:
        raise ElfError('sem tabela de secoes')

    sections = []
    for i in range(e_shnum):
        off = e_shoff + i * e_shentsize
        if is64:
            name, stype, flags, addr, offset, size = struct.unpack_from(
                end + 'IIQQQQ', data, off)
        else:
            name, stype, flags, addr, offset, size = struct.unpack_from(
                end + 'IIIIII', data, off)
        sections.append({'name_off': name, 'type': stype, 'flags': flags,
                         'offset': offset, 'size': size, 'index': i,
                         'hdr_off': off})

    shstr = sections[e_shstrndx]
    strtab = bytes(data[shstr['offset']:shstr['offset'] + shstr['size']])
    for s in sections:
        end_pos = strtab.find(b'\x00', s['name_off'])
        s['name'] = strtab[s['name_off']:end_pos].decode('utf-8', 'replace')

    return data, sections, is64, end, e_shoff, e_shentsize, e_shnum, e_shstrndx


def should_strip(section):
    name = section['name']
    if name in NEVER_STRIP:
        return False
    # SHT_NOBITS (8) nao ocupa espaco no arquivo
    if section['type'] == 8:
        return False
    # Secoes carregadas na memoria sao necessarias em tempo de execucao
    if section['flags'] & SHF_ALLOC:
        return False
    if name in STRIP_EXACT:
        return True
    return any(name.startswith(p) for p in STRIP_PREFIXES)


def strip_file(path, dry_run=False):
    """
    Remove as secoes de depuracao truncando o arquivo.

    Estrategia conservadora: em vez de reconstruir o ELF (que exigiria
    reescrever todos os offsets), aproveitamos que as secoes nao alocadas ficam
    depois de todo o conteudo carregavel. Removemos a tabela de secoes e tudo
    o que vem a partir do menor offset removivel -- o resultado continua
    valido para o carregador dinamico, que usa apenas program headers.
    """
    try:
        data, sections, is64, end, e_shoff, e_shentsize, e_shnum, e_shstrndx = \
            _read_elf(path)
    except (ElfError, struct.error) as exc:
        return None, f'ignorado ({exc})'

    original_size = len(data)
    removable = [s for s in sections if should_strip(s)]
    if not removable:
        return 0, 'nada a remover'

    # Menor offset entre as secoes removiveis e a tabela de secoes.
    # Tudo a partir dai e descartavel: sao metadados de depuracao/ligacao.
    cut = min(min(s['offset'] for s in removable), e_shoff)

    # Seguranca: nunca cortar antes do fim da ultima secao que precisa existir.
    # O .shstrtab e excluido desta conta: ele so guarda os NOMES das secoes e
    # deixa de fazer sentido quando a tabela de secoes e removida. Como ele
    # costuma ser o ultimo item do arquivo, inclui-lo aqui bloquearia qualquer
    # remocao.
    keep_end = 0
    for s in sections:
        if should_strip(s) or s['type'] == 8 or s['name'] == '.shstrtab':
            continue
        keep_end = max(keep_end, s['offset'] + s['size'])
    if cut < keep_end:
        # Layout incomum: as secoes de depuracao estao no meio do arquivo.
        # Nao mexemos, para nao arriscar corromper a biblioteca.
        return 0, 'layout nao suportado, preservado'

    saved = original_size - cut
    if saved <= 0:
        return 0, 'nada a remover'

    if not dry_run:
        new_data = data[:cut]
        # Zera a referencia a tabela de secoes: ela nao existe mais.
        # O carregador dinamico nao a utiliza; ferramentas de analise passam a
        # ver o arquivo como "sem secoes", o que e valido.
        if is64:
            struct.pack_into(end + 'Q', new_data, 0x28, 0)
            struct.pack_into(end + 'H', new_data, 0x3C, 0)
            struct.pack_into(end + 'H', new_data, 0x3E, 0)
        else:
            struct.pack_into(end + 'I', new_data, 0x20, 0)
            struct.pack_into(end + 'H', new_data, 0x30, 0)
            struct.pack_into(end + 'H', new_data, 0x32, 0)
        with open(path, 'wb') as fh:
            fh.write(new_data)

    return saved, f"{len(removable)} secoes"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    dry_run = '--dry-run' in sys.argv
    if not args:
        print(__doc__)
        return 1

    targets = []
    for arg in args:
        if os.path.isdir(arg):
            for root, _, files in os.walk(arg):
                targets.extend(os.path.join(root, f) for f in files
                               if f.endswith('.so'))
        elif arg.endswith('.so'):
            targets.append(arg)

    total_saved = 0
    changed = 0
    for path in sorted(targets):
        saved, note = strip_file(path, dry_run)
        if saved is None:
            continue
        if saved > 0:
            changed += 1
            total_saved += saved
            print(f"  {saved / 1048576:7.2f} MB  {path}  ({note})")

    verb = 'economizaria' if dry_run else 'economizado'
    print(f"\n{changed} arquivo(s), {total_saved / 1048576:.1f} MB {verb}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
