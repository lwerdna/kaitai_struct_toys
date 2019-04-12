#!/usr/bin/env python

# parse the file, drop into a python PDB REPL

from __future__ import print_function

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
	assert len(sys.argv) == 3

	cmd = sys.argv[1]
	fpath = sys.argv[2]

	if cmd == 'dump0':
		kshelp.setFieldExceptionLevel0()
	elif cmd == 'dump1':
		kshelp.setFieldExceptionLevel1()
	elif cmd == 'dump2':
		kshelp.setFieldExceptionLevel2()

	parsed = kshelp.parseFpath(fpath)
	kshelp.exercise(parsed)
	pdb.set_trace() 

