#!/usr/bin/env python

import re
import os
import sys
import kshelp
import urwid

import kaitaistruct

class KaitaiTreeWidget(urwid.TreeWidget):
	""" Display widget for leaf nodes """
	def get_display_text(self):
		# default display will be "key: value"
		return urwid.TreeWidget.get_display_text(self)

		#ksobj = self.get_node().get_value()
		#return kshelp.objToStr(ksobj)

class KaitaiNode(urwid.TreeNode):
	# same as TreeNode constructor + ksobj
	def __init__(self, value, ksobj, parent=None, key=None, depth=None):
		self._ksobj = ksobj
		urwid.TreeNode.__init__(self, value, parent=parent, key=key, depth=depth)

	def load_widget(self):
		return KaitaiTreeWidget(self)

class KaitaiParentNode(urwid.ParentNode):
	# same as ParentNode constructor + ksobj
	def __init__(self, value, ksobj, parent=None, key=None):
		self._ksobj = ksobj

		# depth is steps from root, count them
		depth = 0
		traveller = ksobj
		while traveller._parent:
			depth += 1
			traveller = traveller._parent

		# if a field description isn't provided, generate it from the ksobj
		if value == None:
			value = kshelp.objToStr(ksobj)

		# parent constructor
		urwid.ParentNode.__init__(
			self,
			value,					# field description		self._value
			key=key,				# field name			self._key
			parent=parent,			#						self._parent
			depth=depth				#						self._depth
		)

	def load_widget(self):
		return KaitaiTreeWidget(self)

	# URWID asks us the names ("keys") of our children
	def load_child_keys(self):
		kshelp.exercise(self._ksobj)
		return kshelp.getFieldNamesPrint(self._ksobj) + kshelp.getFieldNamesDescend(self._ksobj)

	# URWID asks us for nodes for each of the names ("keys") of our children
	def load_child_node(self, key):
		childObj = getattr(self._ksobj, key)

		if isinstance(childObj, kaitaistruct.KaitaiStruct):
			return KaitaiParentNode(None, childObj, parent=self, key=key)
		else:
			return KaitaiNode(kshelp.objToStr(childObj), childObj, parent=self, key=key, depth=self.get_depth()+1)

class KaitaiTreeBrowser:
	palette = [
		#('body', 'black', 'light gray'),
		('body', 'light gray', 'black'),
		('focus', 'light gray', 'dark blue', 'standout'),
		('head', 'yellow', 'black', 'standout'),
		('foot', 'light gray', 'black'),
		('key', 'light cyan', 'black','underline'),
		('title', 'white', 'black', 'bold'),
		('flag', 'dark gray', 'light gray'),
		('error', 'dark red', 'light gray'),
		('selectedwidget', 'dark red', 'black')
		]

	footer_text = [
		('title', "Kaitai Data Browser"), "	",
		('key', "UP"), ",", ('key', "DOWN"), ",",
		('key', "PAGE UP"), ",", ('key', "PAGE DOWN"),
		"  ",
		('key', "+"), ",",
		('key', "-"), "  ",
		('key', "LEFT"), "  ",
		('key', "HOME"), "  ",
		('key', "END"), "  ",
		('key', "Q"),
		]

	def __init__(self, ksobj=None):
		self.topnode = KaitaiParentNode(None, ksobj, key='root')
		self.listbox = urwid.TreeListBox(urwid.TreeWalker(self.topnode))
		self.listbox.offset_rows = 0
		self.header = urwid.Text( "" )
		self.footer = urwid.AttrWrap( urwid.Text( self.footer_text ),
			'foot')
		self.view = urwid.Frame(
			urwid.AttrWrap( self.listbox, 'body' ),
			header=urwid.AttrWrap(self.header, 'head' ),
			footer=self.footer )

	def main(self):
		"""Run the program."""

		self.loop = urwid.MainLoop(self.view, self.palette,
			unhandled_input=self.unhandled_input)
		self.loop.run()

	def unhandled_input(self, k):
		if k in ('q','Q'):
			raise urwid.ExitMainLoop()

#------------------------------------------------------------------------------
# main
#------------------------------------------------------------------------------

if __name__ == '__main__':
	assert len(sys.argv) == 3
	(cmd, fpath) = (sys.argv[1], sys.argv[2])

	#kshelp.fieldPrintExceptionsPatterns += [r'^__.*__$']
	# level0 shows the rawest data returned by kaitai
	if cmd == 'level0':
		kshelp.setFieldExceptionLevel0()
	elif cmd == 'level1':
		kshelp.setFieldExceptionLevel1()
	elif cmd == 'level2':
		kshelp.setFieldExceptionLevel2()

	ksobj = kshelp.parseFpath(fpath)

	KaitaiTreeBrowser(ksobj).main()
	#dumpDict(treeDict, 0)
