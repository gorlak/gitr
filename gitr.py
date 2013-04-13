#!/usr/bin/python

import sys
import re
import os
import subprocess
import pprint


# Todo:
#  * make path referencing uniformly relative to rootPath (instead of cwd since it changes)
#  * allow user defined groups of modules driven by .gitrecurse config files
#  * write a prettier status task than git provides
#  * express more actionable information in status
#  * write a better diff command than git provides (show module commit descriptions)


#
# Helpers
#

def die( err ):
	print( err )
	exit( 1 )

rootPath = os.getcwd()
prevPath = []

def pushPath( path ):
	prevPath.append( os.path.abspath( os.getcwd() ) )
	#print( ">>> " + os.path.abspath( path ) )
	os.chdir( os.path.abspath( path ) )

def popPath():
	path = prevPath.pop()
	#print( "<<< " + path )
	os.chdir( path )

def run( cmd ):
	print( "\n\n" + os.path.relpath( os.getcwd(), rootPath ) + " > " + cmd )
	os.system( cmd )

def runAndCapture( cmd ):
	result = []
	proc = subprocess.Popen( cmd, shell=True, stdout=subprocess.PIPE )
	for line in proc.stdout:
		result.append( line.decode("utf-8") );
	return result

def runRecursive( cmd ):
	run( cmd )
	result = runAndCapture( "git submodule" )
	for line in result:
		submodule = parseSubmoduleStatus( line )
		#pprint.pprint( submodule )

		pushPath( submodule[ "path" ] )
		runRecursive( cmd )
		popPath()

def parseSubmoduleStatus( status ):
	match = re.match( "([\+\- ])(\w+) (.*) \((.*)\)", status )
	if match:
		result = {}
		result[ 'commit' ] = match.group( 2 )
		result[ 'dirty' ] = True if match.group( 1 ) == "+" else False
		result[ 'new' ] = True if match.group( 1 ) == "-" else False
		result[ 'path' ] = match.group( 3 )
		matchBranch = re.match( "^heads\/(.*)$", match.group( 4 ) )
		if ( matchBranch ):
			result[ 'branch' ] = matchBranch.group( 1 )
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
	runRecursive( cmd.strip() )
	
def fetch():
	cmd = "git fetch --recurse-submodules=yes"
	run( cmd )

def pull():
	cmd = "git pull"
	run( cmd )

	result = runAndCapture( "git submodule" )
	for line in result:
		submodule = parseSubmoduleStatus( line )
		#pprint.pprint( submodule )

		if submodule[ "new" ]:
			run( "git submodule init -- " + submodule[ "path" ] )
		if submodule[ "dirty" ]:
			if "branch" in submodule:
				pushPath( submodule[ "path" ] )
				pull()
				popPath()
			else:
				run( "git submodule update -- " + submodule[ "path" ] )

def status():
	result = runAndCapture( "git submodule" )
	for line in result:
		submodule = parseSubmoduleStatus( line )
		pprint.pprint( submodule )

		pushPath( submodule[ "path" ] )
		status()
		popPath()

task = None
if len( sys.argv ) > 1:
	if sys.argv[1] in locals():
		task = locals()[ sys.argv[1] ];
	else:
		print( "\nUnknown command: " + sys.argv[1] + "\n" )

if ( task != None ):
	task();
else:
	print( "Usage: " + sys.argv[0] + " <command> [arguments]" )
	print( "\n Commands:" )
	print( "  do     -- execute a command in the current and submodule workspaces" )
	print( "  fetch  -- fetch from current and submodule remotes" )
	print( "  pull   -- pull from current and submodule remotes" )
	print( "  status -- enhanced status information about submodules")

