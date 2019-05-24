#!/usr/bin/env python

import re
import sys
assert sys.version_info[0] == 3
from subprocess import Popen, PIPE

import kshelp

def run(cmd):
	print(' '.join(cmd))
	process = Popen(cmd, stdout=PIPE)
	(stdout, stderr) = process.communicate()
	stdout = stdout.decode("utf-8")
	process.wait()
	return stdout

def ksObjToNode(ksobj, id_):
	kshelp.exercise(ksobj)

	result = ''
	result += '\t"%s" [\n' % id_

	print(repr(ksobj))
	title = re.match(r'<.*\.(.*) object at .*', repr(ksobj)).group(1)

	fieldDescriptions = ['<title> [%s]' % title]

	# add non-KaitaiStruct fields
	for candidate in sorted(kshelp.getFieldNamesPrint(ksobj)):
		tmp = repr(candidate)
		tmp = tmp.replace('"', '\\"')
		if tmp.startswith('\'') and tmp.endswith('\''):
			tmp = tmp[1:-1]
		fieldDescriptions.append('<%s> .%s' % (tmp, tmp))

	# add KaitaiStruct fields
	for candidate in sorted(kshelp.getFieldNamesDescend(ksobj)):
		fieldDescriptions.append('<%s> .%s' % (candidate, candidate))

	result += '\t\tlabel = "%s"\n' % ('|'.join(fieldDescriptions))
	result += '\t\tshape = "record"\n'
	result += '\t];\n'
	
	return result

def ksObjToDot(ksobj):
	dot = ''
	dot += 'digraph g {\n'
	dot += '	graph [\n'
	dot += '		rankdir=LR, overlap=false\n'
	dot += '	];\n'
	dot += '	node [\n'
	dot += '		fontsize = "16"\n'
	dot += '		shape = "ellipse"\n'
	dot += '	];\n'
	dot += '	edge [\n'
	dot += '	];\n'
	
	kshelp.exercise(ksobj)
	ksObjs = kshelp.getLinkedKaitaiObjectsAll(ksobj)

	ksObjToLabel = {}
	for (i,obj) in enumerate(ksObjs):
		ksObjToLabel[obj] = 'ksobj%d'%i

	# declare nodes
	for ksobj in ksObjs:
		label = ksObjToLabel[ksobj]
		dot += ksObjToNode(ksobj, label)

	# declare edges
	id_ = 0
	for srcObj in ksObjs:
		for fieldName in kshelp.getFieldNamesDescend(srcObj):
			# fieldName can be a KaitaiStruct or a [KaitaiStruct, ...]
			# normalize to list...
			dstObjs = None
			try:
				dstObjs = getattr(srcObj, fieldName)
			except AttributeError:
				continue

			if not isinstance(dstObjs, list):
				dstObjs = [dstObjs]

			# loop over list
			for dstObj in dstObjs:
				if not srcObj in ksObjToLabel or not dstObj in ksObjToLabel:
					continue

				srcName = ksObjToLabel[srcObj]
				dstName = ksObjToLabel[dstObj]

				dot += '\t"%s":%s -> "%s":title [\n' % (srcName, fieldName, dstName)
				dot += '\t\tid = %d' % id_
				id_ += 1
				dot += '\t];\n'

	dot += '}\n'

	return dot

#------------------------------------------------------------------------------
# main
#------------------------------------------------------------------------------

if __name__ == '__main__':
	assert len(sys.argv) == 3
	(cmd, fpath) = (sys.argv[1], sys.argv[2])

	kshelp.fieldPrintExceptionsPatterns += [r'^__.*__$']
	# graph0 shows the rawest data returned by kaitai
	if cmd == 'graph0':
		kshelp.setFieldExceptionLevel0()
	elif cmd == 'graph1':
		kshelp.setFieldExceptionLevel1()
	elif cmd == 'graph2':
		kshelp.setFieldExceptionLevel2()

	parsed = kshelp.parseFpath(fpath)
	with open('/tmp/tmp.dot', 'w') as fp:
		fp.write(ksObjToDot(parsed))

	run(['dot', '/tmp/tmp.dot', '-Tpng', '-o/tmp/tmp.png'])
	run(['open', '/tmp/tmp.png'])

