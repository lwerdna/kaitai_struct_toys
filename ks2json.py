#!/usr/bin/env python

import sys
assert sys.version_info[0] == 3
import types

import kaitaistruct
import kshelp

#------------------------------------------------------------------------------
# text dumping stuff
#------------------------------------------------------------------------------

def dump(obj, depth=0):
	print('%s{' % ('\t'*depth))
	depth += 1
	
	print('%s"_kaitai_type": "%s",' % (('\t'*depth), kshelp.objToStr(obj)))

	kshelp.exercise(obj)

	fieldNamesPrint = kshelp.getFieldNamesPrint(obj)
	fieldNamesDescend = kshelp.getFieldNamesDescend(obj)
	fieldNamesAll = fieldNamesPrint + fieldNamesDescend
	for (i,fieldName) in enumerate(fieldNamesAll):
		subObj = None
		try:
			subObj = getattr(obj, fieldName)
		except Exception:
			continue
		if subObj == None:
			continue

		# simple fields
		if fieldName in fieldNamesPrint:
			subObjStr = kshelp.objToStr(subObj)
			print('%s"%s": "%s"' % (('\t'*depth), fieldName, subObjStr), end='')
		# kaitai struct (descend!)
		else:
			if isinstance(subObj, list):
				print('%s"%s":\n%s[' % (('\t'*depth), fieldName, ('\t'*depth)))
				for (j, tmp) in enumerate(subObj):
					#print('%s.%s[%d]:' % (('\t'*depth), fieldName, i))
					dump(tmp, depth+1)
					if j!=len(subObj)-1:
						print(',')
					else:
						print('')
				print('%s]' % ('\t'*depth), end='')
			else:
				print('%s"%s":' % (('\t'*depth), fieldName))
				dump(subObj, depth)

		# add comma?
		if i!=len(fieldNamesAll)-1:
			print(',')
		else:
			print('')

	depth -= 1
	print('%s}' % ('\t'*depth), end='')

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
	dump(parsed)

