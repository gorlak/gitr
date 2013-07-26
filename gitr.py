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
	#print( ">>> " + os.path.abspath( path ) )
	os.chdir( os.path.abspath( path ) )

def popPath():
	path = prevPath.pop()
	#print( "<<< " + path )
	os.chdir( path )

def run( cmd ):
	if verbose:
		print( "\n[" + os.path.relpath( os.getcwd(), rootPath ) + "]: " + cmd )
	return os.system( cmd )

def runAndCapture( cmd ):
	output = []
	if verbose:
		print( "\n[" + os.path.relpath( os.getcwd(), rootPath ) + "]: " + cmd )
	proc = subprocess.Popen( cmd, shell=True, stdout=subprocess.PIPE )

	for line in proc.stdout:
		output.append( line.decode("utf-8") );

	proc.wait() # sets .returncode
	result = collections.namedtuple('Result', ['code', 'output'])
	return result( proc.returncode, output )

def runRecursive( cmd ):
	code = run( cmd )
	if failed( code ):
		return code

	result = runAndCapture( "git submodule" )
	if ( failed( result.code ) ):
		return result.code

	for line in result.output:
		#pprint.pprint( line )
		submodule = parseSubmoduleStatus( line )
		#pprint.pprint( submodule )

		pushPath( submodule[ "path" ] )
		code = runRecursive( cmd )
		popPath()

		if failed( code ):
			return code

def parseSubmoduleStatus( status ):
	match = re.match( "([\+\- ])(\w+) (.*) \((.*)\)", status )
	if match:
		result = {}
		result[ 'commit' ] = match.group( 2 )
		result[ 'dirty' ] = True if match.group( 1 ) == "+" else False
		result[ 'new' ] = True if match.group( 1 ) == "-" else False
		result[ 'path' ] = match.group( 3 )
		return result
	else:
		die( "Unable to parse submodule status: " + status )

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

	code = runRecursive( cmd.strip() )
	if failed( code ):
		exit( code )

	return 0

def fetch():

	cmd = "git fetch --recurse-submodules=yes"
	code = run( cmd )
	if failed( code ):
		exit( code )

	return 0

def headless( isRoot = True ):

	if not isRoot:
		cmd = "git rev-parse HEAD"
		result = runAndCapture( cmd )
		if failed( result.code ):
			print( cmd + " returned " + str( result.code ) + ", exiting with that code" )
			exit( result.code )

		# `git checkout <commit>` won't touch workspace files, see git docs
		cmd = "git checkout -q " + result.output[0]
		code = run( cmd )
		if failed( code ):
			print( cmd + " returned " + str( code ) + ", exiting with that code" )
			exit( code )

	result = runAndCapture( "git submodule" )
	if failed( result.code ):
		print( cmd + " returned " + str( result.code ) + ", exiting with that code" )
		exit( code )

	for line in result.output:
		#pprint.pprint( line )
		submodule = parseSubmoduleStatus( line )
		#pprint.pprint( submodule )

		pushPath( submodule[ "path" ] )
		headless( False )
		popPath()

	return 0

def pull( commitToCheckoutIfNotBranched = None ):

	cmd = "git status --porcelain"
	result = runAndCapture( cmd )
	if failed( result.code ):
		print( cmd + " returned " + str( result.code ) + ", exiting with that code" )
		exit( result.code )

	if len( result.output ):
		print( "Please commit before pulling" )
		exit( 1 )

	cmd = "git branch"
	result = runAndCapture( cmd )
	if failed( result.code ):
		print( cmd + " returned " + str( result.code ) + ", exiting with that code" )
		exit( result.code )

	isBranched = None
	match = re.match( "\* \(no branch\)", result.output[0] )
	if match:
		isBranched = False
	else:
		isBranched = True

	if isBranched:
		print( "pulling " + currentPath() )
		cmd = "git pull"
		code = run( cmd )
		if failed( code ):
			print( cmd + " returned " + str( code ) + ", exiting with that code" )
			exit( code )
	else:
		if not commitToCheckoutIfNotBranched:
			print( "root is not on a branch" )
			exit( 1 )

		cmd = "git rev-parse HEAD"
		result = runAndCapture( cmd )
		if failed( result.code ):
			print( cmd + " returned " + str( result.code ) + ", exiting with that code" )
			exit( result.code )

		if result.output[0].strip() != commitToCheckoutIfNotBranched.strip():
			print( "checking out " + currentPath() + " to " + commitToCheckoutIfNotBranched )
			cmd = "git reset -q --hard " + commitToCheckoutIfNotBranched
			code = run( cmd )
			if failed( code ):
				print( cmd + " returned " + str( code ) + ", exiting with that code" )
				exit( code )

	result = runAndCapture( "git submodule status" )
	if failed( result.code ):
		print( cmd + " returned " + str( result.code ) + ", exiting with that code" )
		exit( code )

	if len( result.output ):
		for line in result.output:
			#pprint.pprint( line )
			submodule = parseSubmoduleStatus( line )
			#pprint.pprint( submodule )

			if submodule[ "new" ]:
				cmd = "git submodule init -- " + submodule[ "path" ]
				code = run( cmd )
				if failed( code ):
					print( cmd + " returned " + str( code ) + ", exiting with that code" )
					exit( code )
			else:
				cmd = "git diff -- " + submodule[ "path" ]
				result = runAndCapture( cmd )
				if ( failed( result.code ) ):
					print( cmd + " returned " + str( code ) + ", exiting with that code" )
					exit( result.code )

				newSubmoduleCommit = None
				for line in result.output:
					match = re.match( "-Subproject commit (.*)", line )
					if match:
						newSubmoduleCommit = match.group(1)

				if newSubmoduleCommit:
					pushPath( submodule[ "path" ] )
					pull( newSubmoduleCommit )
					popPath()

	return 0

def status():

	cmd = "git branch"
	result = runAndCapture( cmd )
	if failed( result.code ):
		print( cmd + " returned " + str( result.code ) + ", exiting with that code" )
		exit( result.code )

	branch = None
	match = re.match( "\* (.*)", result.output[0] )
	if match and match.group(1) != "(no branch)":
		branch = match.group(1)

	if branch:
		print( currentPath() + " is on branch " + branch )
	else:
		print( currentPath() + " is headless" )

	result = runAndCapture( "git submodule" )
	if failed( result.code ):
		exit( result.code )

	for line in result.output:
		#pprint.pprint( line )
		submodule = parseSubmoduleStatus( line )
		#pprint.pprint( submodule )

		pushPath( submodule[ "path" ] )
		status()
		popPath()

	return 0

def update():

	cmd = "git submodule update --init --recursive"
	code = run( cmd )
	if failed( code ):
		exit( code )

task = None
if len( sys.argv ) > 1:
	if sys.argv[1] in locals():
		task = locals()[ sys.argv[1] ];
	else:
		print( "\nUnknown command: " + sys.argv[1] + "\n" )

if ( task != None ):
	exit( task() )
else:
	print( "Usage: " + sys.argv[0] + " <command> [arguments]" )
	print( "\n Commands:" )
	print( "  do       -- execute a command in the current and submodule workspaces" )
	print( "  fetch    -- shorthand for `git fetch --recurse-submodules=yes`" )
	print( "  headless -- change all submodules to not follow any branch (headless checkout of HEAD)" )
	print( "  pull     -- fetch and merge such that submodules following branches pull to the latest branch HEAD" )
	print( "  status   -- enhanced status information about submodules")
	print( "  update   -- shorthand for `git submodule update --init --recursive`" )
