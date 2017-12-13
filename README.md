# Autograder
An automatic project and lab grader

Usage: python3 checkLabs.py -d <folder> -o <output file> -t <tester file> [-v] [-s <seed>] [-to <timeout>] [-tpt] -p <plugins>

-d: Directory - The directory to find files to run

-o: Output - The name of the tab delimeted output file

-t: Tester - The name of the tester file to use e.g. 'testerExample.py'

-v: Verbose - More output

-s: Seed - Use the given seed for randomness in all the tests, leave blank to have different randomness

-to: Timeout - How long to wait before killing the thread

-tpt: Timeout per test - Is the timeout per test? or the whole run

-p: Plugins - A comma seperated list of plugins to use e.g. countSteps,badFunCheck,plagCheck

Example:  python3 checkLabs.py -d 'Project 5' -o P5grades.txt -t tester5p.py -v -s 0 -to 10 -tpt -p countSteps,badFunCheck,plagCheck

