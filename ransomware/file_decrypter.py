#!/usr/bin/env/python3
# file: file_decrypter.py >> decrypt all Fernet 32-byte URL-safe-encrypted files in dir

import sys
import os
from cryptography.fernet import Fernet

files = []

# generate file list of cwd, omit this script and other dirs
for file in os.listdir():
	if file == sys.argv[0] or file.endswith('.key') or file.endswith('.py'):
		continue
	if os.path.isfile(file):	
		files.append(file)

prompt = input(f'Queued following files for decryption: {files}, proceed? ')
if prompt.lower() != 'y':
	sys.exit('Process cancelled by user, exiting ..')

print(f'Decrypting {len(files)} files..')

# scan for keyfile
for file in os.listdir():
	if file.endswith('.key'):
		print('Found keyfile:', file)
		with open(file, 'rb') as keyfile:
			thekey = keyfile.read()

# decrypt files
for file in files:
	with open(file, 'rb') as target:
		contents = target.read()
		contents_decrypted = Fernet(thekey).decrypt(contents)
	with open(file, 'wb') as target:
		target.write(contents_decrypted)

print('DONE')
