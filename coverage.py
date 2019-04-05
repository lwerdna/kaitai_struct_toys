#!/usr/bin/env python

import os
import sys
assert sys.version_info[0] == 3

import kaitaistruct
import kshelp

from PIL import Image, ImageDraw
import colorsys

width = 1024
height = 768
widthBar = 16
fsize = None
img = None
draw = None
def drawRange(start, end, depth):
	y0 = height * (1.0*start / fsize)
	y1 = height * (1.0*(end-1) / fsize)
	x0 = depth*widthBar
	x1 = x0+(widthBar-2)
	# hue is what percentage through the file that the CENTER of this interval is
	hue = ((end+start)/2.0)/fsize
	rgb = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
	rgb = tuple(map(lambda x: int(255*x), rgb))
	#print('drawing rectangle (%d,%d), (%d,%d)' % (x0,y0,x1,y1))
	#draw.rectangle([(x0,y0), (x1,y1)], outline=(0,0,0), fill=rgb)
	draw.rectangle([(x0,y0), (x1,y1)], fill=rgb)
	draw.line((x0,y0,x1,y0), fill=(0,0,0))

def coverage(obj, depth=0, doDraw=False):
	kshelp.exercise(obj)

	indent = '    '*depth
	
	queue = []

	# printable (non descendable field names)
	for fieldName in kshelp.getFieldNamesPrint(obj) + kshelp.getFieldNamesDescend(obj):
		try:
			subObj = getattr(obj, fieldName)
		except Exception:
			continue

		fieldRange = kshelp.getFieldRange(obj, fieldName, True)
		if not fieldRange:
			#print('rejecting %s since it has no range' % fieldName)
			continue
		print('%s.%s covers [0x%x, 0x%X)' % (indent, fieldName, fieldRange[0], fieldRange[1]))
		if doDraw:
			drawRange(fieldRange[0], fieldRange[1], depth)

		if isinstance(subObj, kaitaistruct.KaitaiStruct):
			#print('queuing %s' % fieldName)
			coverage(subObj, depth+1, doDraw)

		if isinstance(subObj, list):
			for i in range(len(subObj)):
				fieldRange = kshelp.getFieldRange(obj, '%s[%d]' % (fieldName, i), True)
				print('%s.%s[%d] covers [0x%x, 0x%X)' % \
					(indent, fieldName, i, fieldRange[0], fieldRange[1]))
				if doDraw:
					drawRange(fieldRange[0], fieldRange[1], depth)

				if isinstance(subObj[i], kaitaistruct.KaitaiStruct):
					coverage(subObj[i], depth+1, doDraw)

def drawFile(fpath):
	global width,height,widthBar,fsize,img,draw

	parsed = kshelp.parseFpath(fpath)

	depth = kshelp.getDepth(parsed)
	width = widthBar * depth
	img = Image.new('RGB', (width, height))
	draw = ImageDraw.Draw(img)
	fsize = os.path.getsize(fpath)
	draw.rectangle([(0,0), (width,height)], fill=(0xC0,0xC0,0xC0))
	#draw.text((5,height-16), fpath, fill=(0,0,0))

	coverage(parsed, 0, True)

	img.save("/tmp/tmp.png")
	os.system('open /tmp/tmp.png')

#------------------------------------------------------------------------------
# main
#------------------------------------------------------------------------------

if __name__ == '__main__':
	assert len(sys.argv) == 3

	kshelp.setFieldExceptionLevel2()

	cmd = sys.argv[1]
	fpath = sys.argv[2]

	if cmd == 'coverage':
		parsed = kshelp.parseFpath(fpath)
		coverage(parsed, 0, False)

	if cmd == 'draw':
		drawFile(fpath)

	if cmd == 'all':
		home = os.environ['HOME']

		fpaths = [ \
			'fdumps/filesamples/hello-linux-x64.elf',
			'fdumps/filesamples/hello-macos-x64.macho',
			'fdumps/filesamples/hello-windows-x86.pe32.exe',
			'fdumps/filesamples/lena.png',
			'fdumps/filesamples/lena.gif',
			'fdumps/filesamples/lena.jpeg',
			'fdumps/filesamples/lena.bmp',
			'fdumps/filesamples/MSPACMAN.zip',
			'fdumps/filesamples/elephbrain.rar',
			'fdumps/filesamples/thttpd-2.29.tar.gz'
		]

		for fpathIn in fpaths:
			fpathOut = '/tmp/%s.png' % os.path.split(fpathIn)[1]
			fpathIn = os.path.join(os.environ['HOME'], fpathIn)
			drawFile(fpathIn)
			os.system('cp /tmp/tmp.png %s' % fpathOut)

