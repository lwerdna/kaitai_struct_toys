#!/usr/bin/env python

import os

if __name__ == '__main__':
	HOME = os.environ['HOME']

	path_formats = os.path.join(HOME, 'repos/lwerdna/kaitai_struct_formats')
	path_output = os.path.join(HOME, 'repos/lwerdna/kaitai_struct_formats/build')
	path_compiler = os.path.join(HOME, 'Downloads/kaitai_struct_compiler/jvm/target/universal/stage/bin/kaitai-struct-compiler')

	import_statements = []

	for folder, subfolder, fnames in os.walk(path_formats):
		if folder.endswith('.git'):
			continue
		if folder.endswith('.circleci'):
			continue
		if folder.endswith('_build'):
			continue

		# compile each
		for fname in fnames:
			if not fname.endswith('.ksy'):
				continue

			path_ksy = os.path.join(folder, fname)
			
			cmd = '%s --debug --target python --import-path %s --outdir %s %s' % \
				(path_compiler, path_formats, path_output, path_ksy)
			print(cmd)
			os.system(cmd)

