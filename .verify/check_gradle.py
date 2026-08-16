#!/usr/bin/env python3
"""Verificacao estrutural de arquivos .gradle (Groovy) sem precisar de JVM.

Nao substitui o compilador Groovy, mas pega a classe de erros que ja quebrou
este build:
  * `gradle`, `project`, `providers` usados dentro de metodo `static`
  * closures/variaveis usados antes de serem declarados
  * delimitadores desbalanceados fora de strings e comentarios

Uso: python3 .verify/check_gradle.py [arquivo.gradle ...]
"""
import re
import sys

# Propriedades do projeto que NAO existem em contexto estatico
PROJECT_PROPS = ("gradle", "project", "providers", "projectDir", "rootProject",
                 "buildDir", "logger", "ext")


def strip_noise(text):
    """Remove comentarios e conteudo de strings, preservando as posicoes."""
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
            # string tripla
            if text[i:i + 3] == q * 3:
                j = text.find(q * 3, i + 3)
                j = n if j == -1 else j + 3
            else:
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


def check_static_scope(clean, path):
    """Metodos `static` nao podem tocar propriedades do projeto."""
    problems = []
    for m in re.finditer(r"^\s*static\s+(?:def|[\w<>\[\]]+)\s+(\w+)\s*\([^)]*\)\s*\{",
                         clean, re.M):
        name = m.group(1)
        # acha o corpo do metodo por contagem de chaves
        depth, i = 0, m.end() - 1
        while i < len(clean):
            if clean[i] == "{":
                depth += 1
            elif clean[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        body = clean[m.end():i]
        for prop in PROJECT_PROPS:
            if re.search(r"\b" + prop + r"\b", body):
                line = clean[:m.start()].count("\n") + 1
                problems.append(
                    f"{path}:{line}: metodo static '{name}' usa '{prop}', "
                    f"que nao existe em contexto estatico")
    return problems


def check_declaration_order(clean, path):
    """Closures `def x = { ... }` devem ser declarados antes do uso."""
    problems = []
    decls = {}
    for m in re.finditer(r"^\s*(?:def|ext\.)\s*(\w+)\s*=\s*\{", clean, re.M):
        decls.setdefault(m.group(1), m.start())
    for name, pos in decls.items():
        for use in re.finditer(r"\b" + name + r"\s*\(", clean):
            if use.start() < pos:
                line = clean[:use.start()].count("\n") + 1
                dline = clean[:pos].count("\n") + 1
                problems.append(
                    f"{path}:{line}: '{name}()' usado antes de ser declarado "
                    f"(declaracao na linha {dline})")
                break
    return problems


def check_balance(clean, path):
    problems = []
    for open_c, close_c, label in (("{", "}", "chaves"),
                                   ("(", ")", "parenteses"),
                                   ("[", "]", "colchetes")):
        a, b = clean.count(open_c), clean.count(close_c)
        if a != b:
            problems.append(f"{path}: {label} desbalanceados: {a} '{open_c}' vs {b} '{close_c}'")
    return problems


def main(paths):
    total = 0
    for path in paths:
        try:
            raw = open(path, encoding="utf-8").read()
        except OSError as e:
            print(f"  ERRO ao ler {path}: {e}")
            total += 1
            continue
        clean = strip_noise(raw)
        problems = (check_balance(clean, path)
                    + check_static_scope(clean, path)
                    + check_declaration_order(clean, path))
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
    args = sys.argv[1:]
    if not args:
        import glob
        args = sorted(glob.glob("*.gradle") + glob.glob("*/build.gradle"))
    sys.exit(main(args))
