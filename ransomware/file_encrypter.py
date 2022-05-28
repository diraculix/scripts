#!/usr/bin/env/python3
# file: file_encrypter.py >> encrypt all files in dir

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

prompt = input(f'Queued following files for encryption: {files}, proceed? ')
if prompt.lower() != 'y':
	sys.exit('Process cancelled by user, exiting ..')

print(f'Encrypting {len(files)} files..')

# generate decryption key
key = Fernet.generate_key()

# write keyfile as binary
with open('decrypt.key', 'wb') as keyfile:
	keyfile.write(key)

# encrypt files
for file in files:
	with open(file, 'rb') as target:
		contents = target.read()
		contents_encrypted = Fernet(key).encrypt(contents)
	with open(file, 'wb') as target:
		target.write(contents_encrypted)

print('DONE')
