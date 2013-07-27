gitr (git-recursive)
====================

gitr is a python script to help recursively act upon git repos and submodules, and generally improve workflow with git submodules.  It allows users to checkout submodules to a branch and keep them merging changes from that branch's tracking branch (instead of updating to a headless commit like `git submodule update` does).

Features
========

gitr pull
---------

A basic usage scenario when working with a repository that uses submodules is:

```
git pull
git submodule update --init --recursive
```

This covers the basics: fetch changes, merge changes from my tracking branch upstream, then update any modules that have changed.  However, if users fail to remember update submodules after pulling, they could very easily roll back the submodule to *their* prior commit with a simple `git commit -a -m` invokation.  Also, if they have commited modifications to submodules in prior commits then the merge strategy to choose the proper submodule commit is murky.

gitr aims to improve submodule workflow in several ways:
* `gitr pull` updates the repository and submodules in a single command.  There are no steps to forget, thus there is a decreased likelihood that other users' commits that change the submodule commit won't be rolled back if the user forgets to update his submodules before making a commit with -a.
* `gitr pull` requires users have a pristine worktree to pull.  As a best practice, being fully committed before pulling ensures the preservation of history of which commit in the submodule was last functional in the parent worktree.  Also, this encourages users to commit any updates of a submodule commit id into the parent repository before pulling the parent.  If there is an uncommitted submodule commit id when doing a pull+update, work could be lost as the subsequent submodule update may completely skip the prior uncomitted submodule commit id (since there is no conflict resolution against uncommitted submodules in the worktree).
* `gitr pull` will perform pull operations (instead of headless checkouts) in submodules if that submodule is checked out to a branch, merging from their tracking branch on the associated remote (it literally runs `git pull` whithin that submodule).  This leaves branches that users have made commits to recently in a branch-checkout state instead of a headless state, which is much more friendly for future commit generation.

gitr headless
-------------

Headless changes every submodule to not be checked out to a branch head, and instead be checked out to a headless commit.  This is useful when one wants to completely reorganize which submodules they want to keep pulling changes automatically via remote branches.  Basically, this command restores the submodules to a checkout state similar to a completely fresh set of initialized submodules.

gitr status
-----------

Status lists which submodules are checked out to branches (and lists the branch they are following), as well as which submodules are checked out to a headless state.  Its very handy for affirming what the behavior of future `gitr pull` operations will be which picking up a crusty repository that hasn't been used recently.

gitr update
-----------

Update is just a shortcut for `git submodule update --init --recursive`.  Sometimes you just want the old tried-and-true behavior built into git without all the keystrokes.

gitr fetch
----------

Fetch is just a shortcut for `git fetch --recurse-submodules=yes`, which actually has slightly different behavior than `git pull`.  This command actually fetches the entire remote repository regardless of whether there is an updated commit into that submodule fetched in the parent.  This is useful for grabbing latest of everything before stepping onto a flight (or any other time you might want all the remote repo contents to be fetched).