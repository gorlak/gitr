#!/usr/bin/python

import sys
import re
import os

# Todo:
#  * stop using foreach in favor of `git submodule status` output, walking cwd through the modules
#  * groups driven by .gitrecurse config files
#  * write a better status command than git provides
#  * write a better diff command than git provides

def run( cmd ):
	print( "\n-> " + cmd )
	os.system( cmd )

def gitAndRecurse( args ):
	cmd = "git " + args + "\n";
	run( cmd ) # operate on the cwd git repo
	args = re.sub( '\"', '\'', args ) # nested calls need single quotes to delimit args (double quotes escape the command)
	cmd = "git submodule foreach --recursive \"git " + args + "\"\n"
	run( cmd ) # recurse to child repos

def do():
	args = ""
	for arg in sys.argv[2:]:
		args += " \"" + arg + "\"";
	gitAndRecurse( args )
	
def clean():
	args = "clean"
	for arg in sys.argv[2:]:
		args += " \"" + arg + "\"";
	gitAndRecurse( args )

def fetch():
	cmd = "git fetch --recurse-submodules=yes"
	run( cmd )

def pull():
	cmd = "git pull --recurse-submodules=yes"
	run( cmd )

cmd = None
if len( sys.argv ) > 1:
	if sys.argv[1] in locals():
		cmd = locals()[ sys.argv[1] ];
	else:
		print( "\nUnknown command: " + sys.argv[1] + "\n" )

if ( cmd != None ):
	cmd();
else:
	print( "Usage: " + sys.argv[0] + " <command> [arguments]" )
	print( "\n Commands:" )
	print( "  do    -- execute a command in the current and submodule workspaces" )
	print( "  clean -- clean (forwards `git clean` options) the current and submodule workspaces" )
	print( "  fetch -- fetch from current and submodule remotes" )
	print( "  pull  -- pull from current and submodule remotes" )
