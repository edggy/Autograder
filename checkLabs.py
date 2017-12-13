import shutil
import os
import sys
import importlib
import unittest
import copy

from collections import defaultdict

from io import StringIO
import threading
import inspect
import ctypes

import argparse

class KillableThread(threading.Thread):
	def _get_my_tid(self):
		"""determines this (self's) thread id"""
		if not self.isAlive():
			raise threading.ThreadError("the thread is not active")

		# do we have it cached?
		if hasattr(self, "_thread_id"):
			return self._thread_id

		# no, look for it in the _active dict
		for tid, tobj in threading._active.items():
			if tobj is self:
				self._thread_id = ctypes.c_long(tid)
				return ctypes.c_long(tid)

		raise AssertionError("could not determine the thread's id")

	def raise_exc(self, exctype):
		"""raises the given exception type in the context of this thread"""
		if not inspect.isclass(exctype):
			raise TypeError("Only types can be raised (not instances)")
		res = ctypes.pythonapi.PyThreadState_SetAsyncExc(self._get_my_tid(), ctypes.py_object(exctype))
		if res == 0:
			raise ValueError("invalid thread id")
		elif res != 1:
			# """if it returns a number greater than one, you're in trouble, 
			# and you should call it again with exc=NULL to revert the effect"""
			ctypes.pythonapi.PyThreadState_SetAsyncExc(self._get_my_tid(), 0)
			raise SystemError("PyThreadState_SetAsyncExc failed")        

	def terminate(self):
		"""raises SystemExit in the context of the given thread, which should 
		cause the thread to exit silently (unless caught)"""
		self.raise_exc(SystemExit)

class TimeoutException(Exception):
	pass

def getArgs():
	parser = argparse.ArgumentParser()

	parser.add_argument("-d", "--targetDirectory",
                        help="directory containing all the students' submissions from Blackboard.",
                        default="./"
                        )
	parser.add_argument("-o", "--output",
                        help="the file to output results",
                        default="./output.txt"
                        )
	parser.add_argument("-t", "--tester",
                        help="the tester file to use",
                        default=None
                        )
	parser.add_argument("-to", "--timeout",
                        help="How much time to give each student",
                        type=int,
                        default=5
                        )      
	parser.add_argument("-v", "--verbosity",
                        action="count",
                        default=0,
                        help="increase output verbosity"
                        )
	parser.add_argument("-s", "--seed",
                        type=int,
                        default=None,
                        help="Seed to use"
                        )
	parser.add_argument("-tpt", "--timeoutPerTest",
                        action="count",
                        default=0,
                        help="If enabled we wait timeout per test instead of timeout per student (default)"
                        )
	parser.add_argument("-p", "--plugins",
                        help="the plugins to use",
                        default=''
                        )    
	args = parser.parse_args()
	return args

def files_list(directory):
	info = os.walk(directory)
	filenames = []
	for (parent, b, filez) in info:
		for file in filez:
			if file != '__init__.py':
				yield os.path.join(parent, file)
		if '__init__.py' not in filez:
			open('__init__.py', 'a').close()

def catchIO(function):
	def wrapper(*args,**kwargs):
		# Store the values of stdin/stdout/stderr
		old_stdout = sys.stdout
		old_stderr = sys.stderr
		old_stdin = sys.stdin

		# Set stdin/stdout/stderr to a StringIO
		sys.stdout = mystdout = StringIO()
		sys.stderr = mystderr = StringIO()

		# Set the stdin just to speed things up
		# Note that we can't kill the thread if waiting for input()...
		sys.stdin = StringIO('A' * 100)

		error = None
		output = None
		try:
			output = function(*args,**kwargs)
		except Exception as e:
			error = e
		finally:
			# Restore the values of stdin/stdout/stderr
			sys.stdout = old_stdout 
			sys.stderr = old_stderr
			sys.stdin = old_stdin

		stdoutput = mystdout.getvalue()
		stderroutput = mystderr.getvalue()

		return output, stdoutput, stderroutput, error
	return wrapper

def runFile(studentFilename, tester, allFiles, stdinput='', plugins = [], **kwargs):
	'''
	Runs a student's file through the tester

	Modifys allFiles and adds studentFilename to dict as a dict with keys: 
	'errors'    - Number of tests that raised an error
	'failures'  - Number of tests with incorrect output
	'numTests'  - Number of tests in total
	'passed'    - Number of tests passed
	'stdout'    - The stdout of running the tests
	'stderr'    - The stderr of running the tests
	'stdsuit'- Output by unittest
	'grade'     - The student's calculated grade on the scale 0.0-1.0 (multiply by 100 to get percentage)

	each as tuples of length 2, the first is for required tests, the second for extra credit

	If there is a class called TheHardcodingTestSuite it will run all the tests in there too (optional)
	'''
	try:
		allFiles[studentFilename] = defaultdict(tuple)
		allFiles[studentFilename]['grade'] = 0
		for p in plugins:
			catchIO(p.init)(allFiles[studentFilename])  
		#keys = {'errors':(),'failures':(),'numTests':(),'passed':(),'stdout':(),'stderr':(),'suitError':(),'grade':0}

		# Create dict to store results

		print(studentFilename)

		try:

			# execute the student's file and catch output, and errors
			data = open(studentFilename).read()
			output, stdoutput, stderroutput, error = catchIO(exec)(data, globals())

			# Add student's code to local scope (it needs to be in tester)
			addErrors = set()
			for functName in tester.REQUIRED_DEFNS + tester.SUB_DEFNS + tester.EXTRA_CREDIT_DEFNS:
				try:
					exec('tester.{funct} = {funct}'.format(funct=functName))
				except NameError:
					print('Add Error: %s' % functName)  
					addErrors.add(functName)

			# create an object that can run tests.
			testout = StringIO()
			runner = unittest.TextTestRunner(stream=testout)

			# define the suite of tests that should be run.
			suites = []
			suites.append(tester.TheTestSuite(tester.REQUIRED_DEFNS + tester.SUB_DEFNS))
			suites.append(tester.TheExtraCreditTestSuite(tester.EXTRA_CREDIT_DEFNS))
			try:
				suites.append(tester.TheHardcodingTestSuite(tester.REQUIRED_DEFNS + tester.SUB_DEFNS + tester.EXTRA_CREDIT_DEFNS))
			except AttributeError:
				pass

			for suite in suites:

				# let the runner run the suite of tests.
				ans, stdoutput, stderroutput, error = catchIO(runner.run)(suite)

				# store the results
				allFiles[studentFilename]['errors'] += (len(ans.errors),)
				allFiles[studentFilename]['failures'] += (len(ans.failures),)
				allFiles[studentFilename]['numTests'] += (ans.testsRun,)
				allFiles[studentFilename]['passed'] += (ans.testsRun - len(ans.errors) - len(ans.failures),)
				allFiles[studentFilename]['stdout'] += (stdoutput,)
				allFiles[studentFilename]['stderr'] += (stderroutput,)
				allFiles[studentFilename]['stdsuit'] += (testout.getvalue(),)

				testout.truncate(0)
				testout.seek(0)

			for p in plugins:
				catchIO(p.run)(data, allFiles[studentFilename])                  

		except (TimeoutException, AttributeError):
			pass

		try:
			# Calculate the grade
			passed = allFiles[studentFilename]['passed']
			allFiles[studentFilename]['grade'] = passed[0]*tester.weight_required + passed[1]*tester.weight_extra_credit
		except IndexError:
			# Calculate the grade
			passed = allFiles[studentFilename]['passed']
			allFiles[studentFilename]['grade'] = passed[0]*tester.weight_required

	except SystemExit:
		pass
	finally:
		# Remove student's code from local scope
		for functName in tester.REQUIRED_DEFNS + tester.SUB_DEFNS + tester.EXTRA_CREDIT_DEFNS:
			try:
				exec('del tester.{funct}'.format(funct=functName))
				exec('del globals()["{funct}"]'.format(funct=functName))
				#exec('del locals()[{funct}]'.format(funct=functName))
			except AttributeError as e:
				print('Delete Error: AttributeError: %s' % e)
			except NameError as e:
				print('Delete Error: NameError: %s' % e)   

		# Cleanup plugins
		for p in plugins:
			catchIO(p.cleanup)(allFiles[studentFilename])          


def runFiles(directory, testerFilename, timeout=5, timeoutPerTest=False, verbose = False, seed = None, pluginNames = []):
	'''
	Run all the files in directory and all subfolders usind the given tester file
	'''

	# A dict from student files to a dict representing the result
	files = {}

	# Remove the extension and import the tester file
	testerName = testerFilename.split('.')[0]
	tester = importlib.import_module(testerName)

	if seed is not None:
		tester.SEED = seed

	plugins = []

	# Create a data dict to pass to the threads
	data = {'studentFilename':None, 'tester':tester, 'allFiles':files, 'stdinput':'', 'plugins':plugins}

	for pn in pluginNames:
		pn = pn.split('.')[0]
		plugin = importlib.import_module(pn)
		plugins.append(plugin)
		catchIO(plugin.start)(data, tester)

	# Iterate over all of the students' files
	for filename in files_list(directory):

		if verbose: print('Running: %s' % (filename))

		# Instantiate files[filename] to be an empty dict and add it to data
		files[filename] = defaultdict(int)
		data['studentFilename'] = filename

		# Create and run a new thread
		t = KillableThread(target=runFile, kwargs=data, daemon=True)
		t.start()

		# Wait for it to finish or for it to timeout
		t.join(timeout=timeout)

		# If the thread didn't finish, kill it
		if t.isAlive():
			if verbose: print('Timed out, killing thread')
			while t.isAlive():
				try:
					t.raise_exc(TimeoutException)
					if timeoutPerTest:
						t.join(timeout=timeout)
					else:
						t.join(timeout=1)
				except (threading.ThreadError, ValueError):
					pass
			if verbose: print('Thread killed')

		if verbose: print('Finished All Test')

	for plugin in plugins:
		catchIO(plugin.end)(data)

	return files

def printResults(fileResults, outputfile, sort=True, seperator='\t'):

	# Sort (or don't sort) the results
	if sort:
		resultList = sorted(fileResults.items(), key=lambda x: x[0])
	else:
		resultList = fileResults.items()

	# Set the format string to None, it will be updated on the first loop
	formatStr = None
	keys = []

	with open(outputfile, 'w') as o:
		for file, result in resultList:

			# Copy the results to data
			data = copy.deepcopy(result)

			# Calculate filename, parent, and grandparent folders
			parent, file = os.path.split(file)
			gparent, lab = os.path.split(parent)

			try:
				# Try to parse the section, username and lab ID (or project ID) from the filename
				data['section'], data['username'], data['labID'] = file.split('_')
				data['labID'] = data['labID'].split('.')[0]
			except ValueError:
				# Parse error, just set the labID to the filename
				data['labID'] = file
				data['section'], data['username'] = None, None

			# Split multiple results into individual keys in the data
			for key, val in result.items():
				try:
					if not isinstance(val, str) and len(val) >= 2:
						try:
							del data[key]
						except KeyError:
							pass
						# Apppend the first key with '-r' (required), 
						# the second with '-ec' (extra credit),
						# and the others with their number
						data['%s-r' % key] = val[0]
						data['%s-ec' % key] = val[1]                        
						for i in range(2, len(val)):
							data['%s-%d' % (key, i)] = val[i]
				except TypeError:
					pass

			# Set the format string to create a header row
			if formatStr is None:
				formatStr = ''
				for key in data:
					keys.append(key)
					if key.startswith('std'):
						formatStr += '{%s!r}%s' % (key, seperator)
					else:
						formatStr += '{%s}%s' % (key, seperator)
				formatStr = formatStr[:-1] + '\n'
				o.write(seperator.join(keys) + '\n')

			# Add missing keys
			for key in keys:
				if key not in data:
					data[key] = None

			# Write the data to the file
			o.write(formatStr.format(**data))    

def main():
	# Parse arguments
	args = getArgs()
	verbose_level = args.verbosity
	verbose = verbose_level > 0
	directory = args.targetDirectory
	outputfile = args.output
	testerFile = args.tester
	timeout = args.timeout
	seed = args.seed
	timeoutPerTest = args.timeoutPerTest
	pluginNames = args.plugins.split(',')

	pluginNames = [x.strip() for x in pluginNames if x.strip()]

	# Run the files
	fileResults = runFiles(directory=directory, verbose=verbose, testerFilename=testerFile, timeout=timeout, timeoutPerTest=timeoutPerTest, seed=seed, pluginNames=pluginNames)

	# Output results to a file
	printResults(fileResults, outputfile)
	print('Done!')

if __name__ == "__main__":
	main()
