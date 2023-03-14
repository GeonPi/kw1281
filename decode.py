#!/usr/bin/python3
import os
import argparse
import sys

def is_complement(n0, n1):
	if(n0 + n1 == 255):
		return True
	else:
		return False

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("-i", "--input",    nargs=1, metavar=('filename'), help="input file")
	parser.add_argument("-v", "--verbose",  action="store_true", help="debug info")
	global args
	args = parser.parse_args()

	numberLines = 0
	with open(args.input[0], "rb") as f:
		with open("output", "w") as fw:
			for line in f:
				numberLines += 1
				n = int(line.split()[0], 2)
				r = int('{:08b}'.format(n)[::-1], 2) 	#reverse

				fw.write(format(n, '{fill}{width}b'.format(width=8, fill=0)) + "\t")
				fw.write(hex(n)[2:].upper() + "\t")
				fw.write(format(r, '{fill}{width}b'.format(width=8, fill=0)) + "\t")					
				fw.write(hex(r)[2:].upper() + "\t")
				if(r > 31 and r < 127):
					fw.write(chr(r) + "\t")
				else:
					fw.write("\t")


				if(numberLines > 1):
					if(is_complement(n, nMinusOne)):
						fw.write("complement\n")
					else:
						fw.write("\n")
						if(args.verbose):
							print(str(hex(n)) + " is complement of " + str(hex(nMinusOne)))
				else:
					fw.write("\n")

				nMinusOne = n

				if(args.verbose):
					print(format(n, '{fill}{width}b'.format(width=8, fill=0)), end="\t")
					print(hex(n)[2:].upper(), end="\t")
					print(format(r, '{fill}{width}b'.format(width=8, fill=0)), end="\t")
					print(hex(r)[2:].upper(), end="\t")
					if(r > 31):
						print(chr(r))
					else:
						print("")
	

	print("\n")


if __name__ == '__main__': 
    main() 