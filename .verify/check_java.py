#!/usr/bin/env python3
"""Verificacao estrutural de arquivos .java sem precisar de JDK.

Nao substitui o compilador, mas pega a classe de erros que ja quebrou builds
deste projeto:

  * "illegal forward reference": inicializador de campo de instancia que
    referencia outro campo declarado DEPOIS dele;
  * delimitadores desbalanceados;
  * imports estaticos orfaos (nao usados).

Uso: python3 .verify/check_java.py <arquivo.java> [...]

Nota: em arquivos muito grandes (>5k linhas) a analise pode demorar. Rode nos
arquivos alterados, nao no projeto inteiro:

    python3 .verify/check_java.py $(git diff --name-only | grep '\.java$')
"""
import re
import sys


def strip_noise(text):
    """Neutraliza comentarios e strings preservando posicoes e quebras de linha."""
    out = []
    i, n = 0, len(text)
    while i < n:
        two = text[i:i + 2]
        if two == "/*":
            j = text.find("*/", i + 2)
            j = n if j == -1 else j + 2
            out.append(re.sub(r"[^\n]", " ", text[i:j]))
            i = j
        elif two == "//":
            j = text.find("\n", i)
            j = n if j == -1 else j
            out.append(" " * (j - i))
            i = j
        elif text[i] in "\"'":
            q = text[i]
            j = i + 1
            while j < n and text[j] != q:
                if text[j] == "\\":
                    j += 1
                j += 1
            j = min(j + 1, n)
            out.append(re.sub(r"[^\n]", " ", text[i:j]))
            i = j
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


FIELD_RE = re.compile(
    r"^[ \t]*(?:private|protected|public)[ \t]+"      # modificador de acesso
    r"(?:static[ \t]+)?(?:final[ \t]+)?"              # static/final opcionais
    r"[\w.<>\[\], ?]+?[ \t]+"                         # tipo
    r"(\w+)[ \t]*=",                                  # nome e atribuicao
    re.M)



METHOD_IN_BODY_RE = re.compile(
    r"(?:@\w+[ \t]*\n?[ \t]*)*"                      # anotacoes (@Override...)
    r"(?:public|private|protected)?[ \t]*"
    r"(?:static[ \t]+)?[\w.<>\[\], ?]+[ \t]+\w+[ \t]*\([^)]*\)[ \t]*\{")


def _strip_method_bodies(body):
    """Remove corpos de metodos declarados dentro do inicializador.

    Ex.: em `new Listener() { public void onX() { campoDepois = 1; } }`
    o acesso a `campoDepois` ocorre em tempo de execucao, nao de inicializacao.
    """
    out = body
    while True:
        m = METHOD_IN_BODY_RE.search(out)
        if not m:
            return out
        i, depth = m.end() - 1, 0
        while i < len(out):
            if out[i] == "{":
                depth += 1
            elif out[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        out = out[:m.start()] + " " * (i + 1 - m.start()) + out[i + 1:]


def depth_at(clean, pos):
    """Profundidade de chaves na posicao dada (1 = corpo da classe externa)."""
    return clean.count("{", 0, pos) - clean.count("}", 0, pos)


def check_forward_reference(clean, path):
    """Campos de instancia nao podem referenciar campos declarados depois.

    Considera apenas campos no corpo da classe externa (profundidade 1); campos
    de classes anonimas ou internas vivem em outro escopo e nao conflitam.
    """
    problems = []
    fields = []           # (nome, pos_declaracao, is_static)
    for m in FIELD_RE.finditer(clean):
        if depth_at(clean, m.start()) != 1:
            continue      # campo de classe anonima/interna
        decl = m.group(0)
        fields.append((m.group(1), m.start(), "static" in decl))

    positions = {name: pos for name, pos, _ in fields}

    for name, pos, is_static in fields:
        # corpo do inicializador: do '=' ate o ';' que fecha (respeitando blocos)
        i = clean.index("=", pos) + 1
        depth = 0
        while i < len(clean):
            c = clean[i]
            if c in "{([":
                depth += 1
            elif c in "})]":
                depth -= 1
            elif c == ";" and depth == 0:
                break
            i += 1
        body = clean[clean.index("=", pos) + 1:i]

        # Java so proibe a referencia quando ela e AVALIADA na inicializacao.
        # Dentro do corpo de um metodo (de classe anonima ou lambda com bloco) a
        # execucao e posterior, entao e legal. Remove esses trechos antes de olhar.
        body_immediate = _strip_method_bodies(body)

        for other, other_pos in positions.items():
            if other == name or other_pos <= pos:
                continue
            if re.search(r"\b" + re.escape(other) + r"\b", body_immediate):
                line = clean[:pos].count("\n") + 1
                oline = clean[:other_pos].count("\n") + 1
                problems.append(
                    f"{path}:{line}: campo '{name}' referencia '{other}', "
                    f"declarado depois (linha {oline}) -> illegal forward reference")
    return problems


def check_balance(clean, path):
    problems = []
    for o, c, label in (("{", "}", "chaves"), ("(", ")", "parenteses"),
                        ("[", "]", "colchetes")):
        a, b = clean.count(o), clean.count(c)
        if a != b:
            problems.append(f"{path}: {label} desbalanceados: {a} '{o}' vs {b} '{c}'")
    return problems


def check_orphan_static_imports(clean, path):
    problems = []
    for m in re.finditer(r"^import static [\w.]+\.(\w+);", clean, re.M):
        name = m.group(1)
        body = clean[m.end():]
        if not re.search(r"\b" + re.escape(name) + r"\s*\(", body):
            line = clean[:m.start()].count("\n") + 1
            problems.append(f"{path}:{line}: import static '{name}' nao utilizado")
    return problems


def main(paths):
    total = 0
    for path in paths:
        try:
            clean = strip_noise(open(path, encoding="utf-8").read())
        except OSError as e:
            print(f"  ERRO ao ler {path}: {e}")
            total += 1
            continue
        problems = (check_balance(clean, path)
                    + check_forward_reference(clean, path)
                    + check_orphan_static_imports(clean, path))
        if problems:
            for p in problems:
                print(f"  {p}")
            total += len(problems)
        else:
            print(f"  {path}: ok")
    print()
    if total:
        print(f"{total} problema(s) encontrado(s)")
        return 1
    print("Nenhum problema estrutural encontrado")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1:]))
