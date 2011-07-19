#!/bin/sed -f
# Simple Sed Program to remove C++ comments from C source-files
# like: // <comment>
s://.*$::g
