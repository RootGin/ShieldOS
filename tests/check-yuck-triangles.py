#!/usr/bin/env python3
import glob
import os
import re
import sys

def tokenize(text):
    tokens = []
    pos = 0
    length = len(text)
    line = 1
    col = 1
    while pos < length:
        ch = text[pos]
        if ch == "\n":
            line += 1
            col = 1
            pos += 1
        elif ch in " \t\r":
            col += 1
            pos += 1
        elif ch == ";":
            while pos < length and text[pos] != "\n":
                pos += 1
        elif ch in "()":
            tokens.append((ch, line, col))
            pos += 1
            col += 1
        elif ch == "\"":
            start_l, start_c = line, col
            pos += 1
            col += 1
            s = []
            while pos < length and text[pos] != "\"":
                if text[pos] == "\\" and pos + 1 < length:
                    s.append(text[pos:pos+2])
                    pos += 2
                    col += 2
                else:
                    if text[pos] == "\n":
                        line += 1
                        col = 1
                    else:
                        col += 1
                    s.append(text[pos])
                    pos += 1
            if pos < length:
                pos += 1
                col += 1
            tokens.append(("\"" + "".join(s) + "\"", start_l, start_c))
        else:
            start_l, start_c = line, col
            start = pos
            while pos < length and text[pos] not in " \t\r\n();\"":
                pos += 1
                col += 1
            tokens.append((text[start:pos], start_l, start_c))
    return tokens

def parse_sexpr(tokens, index=0):
    if index >= len(tokens):
        return None, index
    tok, l, c = tokens[index]
    if tok == "(":
        items = []
        cur = index + 1
        while cur < len(tokens) and tokens[cur][0] != ")":
            item, cur = parse_sexpr(tokens, cur)
            if item is not None:
                items.append(item)
        if cur < len(tokens) and tokens[cur][0] == ")":
            cur += 1
        return (items, l, c), cur
    elif tok == ")":
        return None, index + 1
    else:
        return (tok, l, c), index + 1

def check_node(node, filename, errors):
    if not isinstance(node, tuple) or not isinstance(node[0], list):
        return
    items, line, col = node
    attrs = {}
    i = 1
    while i < len(items):
        item = items[i]
        if isinstance(item, tuple) and isinstance(item[0], str) and item[0].startswith(":"):
            attr_name = item[0]
            val = items[i+1][0] if i+1 < len(items) and isinstance(items[i+1], tuple) and isinstance(items[i+1][0], str) else ""
            attrs[attr_name] = val
            i += 2
        else:
            check_node(item, filename, errors)
            i += 1
    cls_val = attrs.get(":class", "").strip("\"")
    if re.search(r"\btriangle(sub)?\b", cls_val):
        if ":width" in attrs or ":height" in attrs:
            dim_err = []
            if ":width" in attrs:
                dim_err.append(":width " + attrs[":width"])
            if ":height" in attrs:
                dim_err.append(":height " + attrs[":height"])
            errors.append(filename + ":" + str(line) + ": Border-only triangle (class \"" + cls_val + "\") must not declare explicit dimensions (" + ", ".join(dim_err) + ")")

def lint_yuck(text, filename="<string>"):
    tokens = tokenize(text)
    cur = 0
    errors = []
    while cur < len(tokens):
        ast, cur = parse_sexpr(tokens, cur)
        if ast:
            check_node(ast, filename, errors)
    return errors

def run_selftest():
    neg_snippet = """
    (overlay
      (box :class "triangle outline bottomright" :width 20 :height 20)
      (box :class "trianglesub bottomleft" :width 18))
    """
    neg_errors = lint_yuck(neg_snippet, "<neg-test>")
    if len(neg_errors) != 2:
        print("FAIL [yuck-geometry-selftest]: Negative test failed to catch explicit dimensions on triangles: " + str(neg_errors), file=sys.stderr)
        sys.exit(1)

    pos_snippet = """
    (overlay :width 20 :height 20
      (box :class "triangle outline bottomright")
      (box :class "trianglesub bottomleft"))
    """
    pos_errors = lint_yuck(pos_snippet, "<pos-test>")
    if len(pos_errors) != 0:
        print("FAIL [yuck-geometry-selftest]: Positive test produced false positives: " + str(pos_errors), file=sys.stderr)
        sys.exit(1)

def main():
    run_selftest()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_dir = os.path.dirname(script_dir)
    yuck_files = [os.path.join(repo_dir, "eww.yuck")] + sorted(glob.glob(os.path.join(repo_dir, "yuck", "*.yuck")))

    total_errors = []
    for path in yuck_files:
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        errs = lint_yuck(content, os.path.relpath(path, repo_dir))
        total_errors.extend(errs)

    if total_errors:
        for err in total_errors:
            print("FAIL [yuck-triangle-geometry]: " + err, file=sys.stderr)
        sys.exit(1)

    print("PASS [seam1-yuck]: Triangle geometry check passed (negative test verified).")

if __name__ == "__main__":
    main()
