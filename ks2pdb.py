#!/usr/bin/env python
# parse the file, drop into a python PDB REPL

import sys
assert sys.version_info[0] == 3
import types

import kaitaistruct
import kshelp

import pdb

#------------------------------------------------------------------------------
# main
#------------------------------------------------------------------------------

if __name__ == '__main__':
	assert len(sys.argv) == 2

	fpath = sys.argv[1]

	parsed = kshelp.parseFpath(fpath)
	kshelp.exercise(parsed)
	pdb.set_trace() 

