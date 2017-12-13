import string
import keyword
from collections import defaultdict


goodFuns_kwds = set(keyword.kwlist)
goodFuns = None

def start(data, tester):
	global goodFuns
	goodFuns = goodFuns_kwds | set(tester.REQUIRED_DEFNS + tester.SUB_DEFNS + tester.EXTRA_CREDIT_DEFNS) | tester.ALLOWED_FUNCTIONS

def init(student):
	student['functions'] = None
	student['functions-loc'] = None

def run(data, student):
	funData = defaultdict(list)
	lineNum = 1
	lastNewline = -1
	commentType = None
	commentChars = []
	for n, c in enumerate(data):
		if c == '#' and commentType is None:
			commentType = '#'

		elif c == '\n' and commentType == '#':
			commentType = None

		# TODO: Block comments
		'''if c == "'" or c == '"' and commentType is None:
            if commentType == "'":
                commentType = None
            else:
                commentType = "'"
        '''

		if commentType is not None:
			commentChars.append(n)

		if c == '\n':
			lineNum += 1
			lastNewline = n
		elif c == '(' and commentType is None:
			word = ''
			i = n - 1
			while data[i] in string.whitespace:
				i -= 1
			while data[i] not in string.whitespace + '.\n':
				word = data[i] + word
				i -= 1
			i += 1
			if word.isidentifier() and word not in goodFuns and i not in commentChars:
				ln, col = lineNum, i - lastNewline
				funData[word].append((ln, col))
	student['functions'] = repr([k for k in sorted(funData.keys())])
	student['functions-loc'] = repr([(k,v) for k, v in sorted(funData.items())])

def cleanup(student):
	pass

def end(data):
	pass


check_horizontal(tester.board11(), 4, 1)'''
