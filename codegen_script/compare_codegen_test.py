from pathlib import Path
import runpy
import sys
import subprocess
import re

import pytest


def test_codegen_differences():
    # subprocess.run("perl codegen.pl")
    # runpy.run_path("codegen.py", run_name="__main__")

    py_codegen_out = Path("../codegen_t")
    perl_codegen_out = Path("../codegen")

    # Perl prints out the hex converted values in proper two's complement,
    # Python doesn't as Python's int doesn't have a set size, so it instead
    # prints it in as signed hex. This difference doesn't matter for
    # us as it's just a comment and perl doesn't get the correct hex
    # representation anyway.
    py_pattern = re.compile(r".*// -\d*, 0x-[\dA-Z]*$")
    perl_pattern = re.compile(r".*// -\d.*, 0x[\dA-Z]*$")
    for path in py_codegen_out.iterdir():
        print(f"testing file {path.name}")
        with open(path, "r") as py_file, open(perl_codegen_out / path.name) as perl_file:
            for py_line, perl_line in zip(py_file, perl_file):
                if py_pattern.match(py_line) and perl_pattern.match(perl_line):
                    continue
                assert py_line == perl_line, f"file {path.name}"
