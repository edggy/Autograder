import sys
import importlib

def tracefunc(frame, event, arg, indent=[0]):
	global steps
	steps += 1

def countSteps(testerFilename, studentFilename):
	global steps
	steps = 0

	sys.settrace(tracefunc)

	testerName = testerFilename.split('.')[0]
	tester = importlib.import_module(testerName)

	import checkLabs

	allFiles = {}

	checkLabs.runFile(studentFilename, tester, allFiles)

	allFiles[studentFilename]['steps'] = steps

	return allFiles

def start(data, tester):
	pass

def init(student):
	global steps
	steps = 0
	sys.settrace(tracefunc)

def run(data, student):
	pass

def cleanup(student):
	global steps
	student['steps'] = steps

def end(data):
	pass

if __name__ == '__main__':
	allFiles = countSteps(sys.argv[1], sys.argv[2])
	print('Steps taken: %s' % steps)
	print(allFiles[sys.argv[2]]['grade'])