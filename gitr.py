#!/usr/bin/python

import sys
import platform
import re
import os
import subprocess
import collections
import pprint

# Todo:
#  * allow user defined groups of modules driven by .gitrecurse config files
#  * submodule removal / relocation via .gitrecurse
#  * commit (depth-first commit generation)

verbose = False

#
# Helpers
#

def die( err ):
	print( err )
	exit( 1 )

def failed( code ):
	if platform.system() == 'Windows':
		return code != 0
	else:
		return code >> 8 != 0 # http://docs.python.org/3.3/library/os.html#os.system

rootPath = os.getcwd()
prevPath = []

def currentPath():
	return os.path.relpath( os.getcwd(), rootPath )

def pushPath( path ):
	prevPath.append( os.path.abspath( os.getcwd() ) )
	os.chdir( os.path.abspath( path ) )

def popPath():
	path = prevPath.pop()
	os.chdir( path )

def run( cmd, exitOnFailure = False ):
	if verbose:
		print( "\n[" + os.path.relpath( os.getcwd(), rootPath ) + "]: " + cmd )

	code = os.system( cmd )

	if exitOnFailure:
		if failed( code ):
			print( cmd + " returned " + str( code ) + ", exiting with that code" )
			exit( code )

	return code

def runAndCapture( cmd, exitOnFailure = False ):
	if verbose:
		print( "\n[" + os.path.relpath( os.getcwd(), rootPath ) + "]: " + cmd )

	proc = subprocess.Popen( cmd, shell=True, stdout=subprocess.PIPE )

	output = []
	for line in proc.stdout:
		output.append( line.decode("utf-8") );

	proc.wait() # sets .returncode
	resultTuple = collections.namedtuple('Result', ['code', 'output'])
	result = resultTuple( proc.returncode, output )

	if exitOnFailure:
		if failed( result.code ):
			print( cmd + " returned " + str( result.code ) + ", exiting with that code" )
			exit( result.code )

	return result

def runRecursive( cmd, exitOnFailure = False ):
	code = run( cmd, exitOnFailure )
	if failed( code ):
		return code

	cmd = "git submodule"
	result = runAndCapture( cmd, exitOnFailure )
	if failed( result.code ):
		return result.code

	for line in result.output:
		submodule = parseSubmoduleStatus( line )
		if submodule[ "path" ][:2] != "..":
			pushPath( submodule[ "path" ] )
			code = runRecursive( cmd, exitOnFailure )
			popPath()

			if failed( code ):
				return code

def parseSubmoduleStatus( status ):
	match = re.match( "([\+\- ])(\w+) (.*) \(.*\)", status ) 
	if not match: # sometimes we don't get a parenthetical at the end of the line
		match = re.match( "([\+\- ])(\w+) (.*)", status )
	if match:
		result = {}
		result[ 'commit' ] = match.group( 2 )
		result[ 'dirty' ] = True if match.group( 1 ) == "+" else False
		result[ 'new' ] = True if match.group( 1 ) == "-" else False
		result[ 'path' ] = match.group( 3 )
		return result
	else:
		die( "Unable to parse submodule status: " + status )

def getBranch( result ):
	for line in result.output:
		match = re.match( "\* (.*)", line )
		if match:
			branch = match.group(1)
			if branch == "(no branch)":
				return None
			else:
				match = re.match( "\(detached from .+\)", branch)
				if match:
					return None
			return branch
	return None

#
# Tasks (callable from the frontend)
#

def do():

	cmd = ""
	for arg in sys.argv[2:]:
		if ' ' in arg:
			cmd += " \"" + arg + "\"";
		else:
			cmd += " " + arg

	return runRecursive( cmd.strip(), exitOnFailure = True )

def fetch():

	return run( "git fetch --recurse-submodules=yes", exitOnFailure = True )

def headless( isRoot = True ):

	if not isRoot:
		result = runAndCapture( "git rev-parse HEAD", exitOnFailure = True )
		run( "git checkout -q " + result.output[0], exitOnFailure = True ) # `git checkout <commit>` won't touch workspace files, see git docs

	result = runAndCapture( "git submodule", exitOnFailure = True )
	for line in result.output:
		submodule = parseSubmoduleStatus( line )
		if submodule[ "path" ][:2] != "..":
			pushPath( submodule[ "path" ] )
			headless( False )
			popPath()

	return 0

def pull( newCommit = None ):

	if getBranch( runAndCapture( "git branch", exitOnFailure = True ) ) != None:
		print( "Pulling " + currentPath() )
		run( "git pull", exitOnFailure = True )
	else:
		if newCommit:
			result = runAndCapture( "git rev-parse HEAD", exitOnFailure = True )
			if result.output[0].strip() != newCommit.strip():
				print( "Fetching tags for " + currentPath() )
				run( "git fetch --tags", exitOnFailure = True )
				print( "Checking out " + currentPath() + " to " + newCommit )
				run( "git reset -q --hard " + newCommit, exitOnFailure = True )

	result = runAndCapture( "git submodule status", exitOnFailure = True )
	if len( result.output ):
		for line in result.output:
			submodule = parseSubmoduleStatus( line )
			if submodule[ "path" ][:2] != "..":
				if submodule[ "new" ]:
					run( "git submodule update --init --recursive -- " + submodule[ "path" ], exitOnFailure = True )
				else:
					result = runAndCapture( "git diff -- " + submodule[ "path" ], exitOnFailure = True )
					newSubmoduleCommit = None
					for line in result.output:
						match = re.match( "-Subproject commit (.*)", line )
						if match:
							newSubmoduleCommit = match.group(1)
					pushPath( submodule[ "path" ] )
					pull( newSubmoduleCommit )
					popPath()

	return 0

def push():

	result = runAndCapture( "git submodule status", exitOnFailure = True )
	if len( result.output ):
		for line in result.output:
			submodule = parseSubmoduleStatus( line )
			if submodule[ "path" ][:2] != "..":
				pushPath( submodule[ "path" ] )
				push()
				popPath()

	if getBranch( runAndCapture( "git branch", exitOnFailure = True ) ) != None:
		print( "Pushing " + currentPath() )
		run( "git push", exitOnFailure = True )

	return 0

def status():

	branch = getBranch( runAndCapture( "git branch", exitOnFailure = True ) )
	if branch:
		print( currentPath() + " is on branch " + branch )
	else:
		print( currentPath() + " is headless" )

	result = runAndCapture( "git submodule", exitOnFailure = True )
	for line in result.output:
		submodule = parseSubmoduleStatus( line )
		if submodule[ "path" ][:2] != "..":
			pushPath( submodule[ "path" ] )
			status()
			popPath()

	return 0

def update():

	return run( "git submodule update --init --recursive", exitOnFailure = True )

task = None
if len( sys.argv ) > 1:
	if sys.argv[1] in locals():
		task = locals()[ sys.argv[1] ];
	else:
		print( "\nUnknown command: " + sys.argv[1] + "\n" )

if task:
	exit( task() )
else:
	print( "Usage: " + sys.argv[0] + " <command> [arguments]" )
	print( "\n Commands:" )
	print( "  do       -- execute a command in the current and submodule workspaces" )
	print( "  fetch    -- shorthand for `git fetch --recurse-submodules=yes`" )
	print( "  headless -- change all submodules to not follow any branch (headless checkout of HEAD)" )
	print( "  pull     -- fetch and merge such that submodules following branches pull to the latest branch HEAD" )
	print( "  push     -- push submodules following branches to their respective remote" )
	print( "  status   -- enhanced status information about submodules")
	print( "  update   -- shorthand for `git submodule update --init --recursive`" )
