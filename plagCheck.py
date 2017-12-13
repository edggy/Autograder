import keyword
import astor
import ast
import hashlib

from collections import defaultdict

# Set this to True to include the normalized code in the output
normalizeCode = False

goodWords = set(dir(__builtins__) + keyword.kwlist)

def start(data, tester):
	global goodFuns
	goodFuns = set(tester.REQUIRED_DEFNS + tester.SUB_DEFNS + tester.EXTRA_CREDIT_DEFNS)

def init(student):
	for funName in goodFuns:
		if normalizeCode:
			student['NormedCode-%s' % funName] = None
		student['SHA256-%s' % funName] = None 
		student['Plag-%s' % funName] = None

def run(data, student):

	def rename(obj, attr, name):
		val = getattr(obj, attr)
		if val in renamings:
			node.id = renamings[val]
		elif val not in goodWords:
			newName = name
			renamings[val] = newName
			setattr(obj, attr, newName)

	functions = [i for i in data.split('def')]
	for f in functions:
		try:
			renamings = {}
			nameID = 1
			namePrefix = 'A%d'    
			tree = ast.parse('def' + f)
			funName = f.split()[0].split('(')[0]
			for node in ast.walk(tree):
				if isinstance(node, ast.FunctionDef):
					if node.name not in goodFuns | goodWords:
						rename(node, 'name', namePrefix % nameID)
						nameID += 1
				elif isinstance(node, ast.Name):  
					rename(node, 'id', namePrefix % nameID)
					nameID += 1
				elif isinstance(node, ast.arguments):
					for arg in node.args:
						rename(arg, 'arg', namePrefix % nameID)
						nameID += 1                
				else:
					pass
			source = astor.to_source(tree, indent_with='\t')
			if normalizeCode:
				student['NormedCode-'+funName] = repr(source)
			student['SHA256-%s' % funName] = hashlib.new('sha256', source.encode("utf_8")).hexdigest()
			print('%s: %s' % (funName, student['SHA256-'+funName]))
		except SyntaxError:
			pass

def cleanup(student):
	pass

def end(data):
	hashes = defaultdict(lambda: defaultdict(set))
	for studentFilename, studentData in data['allFiles'].items():
		for key, shaHash in studentData.items():
			if key.startswith('SHA256-'):
				funName = '-'.join(key.split('-')[1:])
				if shaHash is not None:
					hashes[funName][shaHash].add(studentFilename)

	for funName, funHashes in hashes.items():
		for shaHash, cheaterRing in funHashes.items():
			if len(cheaterRing) > 1:
				for studentFilename in cheaterRing:
					data['allFiles'][studentFilename]['Plag-%s' % funName] = repr(cheaterRing)

if __name__ == '__main__':
	data = '''def read_file(filename):
    db = {}
    with open(filename) as fh:
        isFirstorNot = True
		#using multiple if statements and for loops
        for line in fh:
            if isFirstorNot:
                isFirstorNot = False
                continue
            if not line:
                continue
            (year, gender, name, count) = line.split('","')
            year = int(obtain_unquoted_string(year))
            gender = obtain_unquoted_string(gender)
            name = obtain_unquoted_string(name)
            count = int(obtain_unquoted_string(count))
            if (name, gender) in db:
                db[(name, gender)].append((year, count, None))
            else:
                db[(name, gender)] = [(year, count, None)]
    for entry in db:
        db[entry].sort()
    return db'''

	data2 = '''def read_file(filename):
	db = {}
	with open(filename) as z:
		i = True
		for l in z:
			if i:
				i = False
				continue
			if not l:
				continue
			(year, gender, name, count) = l.split('","')
			year = int(unqouted(year))
			gender = unqouted(gender)
			name = unqouted(name)
			count = int(unqouted(count))
			if (name, gender) in db:
				db[name, gender].append((year, count, None))
			else:
				db[name, gender] = [(year, count, None)]
	for x in db:
		db[x].sort()
	return db'''
	source1 = run(data, {})
	source2 = run(data2, {})

	print(source1 == source2)
