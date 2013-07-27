gitr (git-recursive)
====================

gitr is a python script to help recursively act upon git repos and submodules.  It allows users to checkout submodules to a branch and keep them merging change from that branch (instead of updating to a headless commit by `git submodule update`).

A basic usage scenario when working with a repository that uses submodules is:

```
git pull
git submodule update --init --recursive
```

This covers the basics: fetch changes, merge changes from my tracking branch upstream, then update any modules that have changed.  However, if users fail to remember update submodules after pulling, they could very easily roll back the submodule to *thier* prior commit with a simple `git commit -a -m` invokation.  Also, if they have commited modifications to submodules in prior commits then the merge strategy to choose the proper submodule commit is murky.

gitr aims to improve submodule workflow in several ways:
* `gitr pull` updates the repository and submodules in a single command.  There are no steps to forget, thus there is a decreased likelihood that other users' commits that change the submodule commit won't be rolled back if the user forgets to update his submodules before making a commit with -a.
* `gitr pull` requires users have a pristine worktree to pull.  This encourages users to commit submodule changes before pulling the parent repository.  As a best practice, being fully committed before pulling ensures the preservation of history of which commit in the submodule was last functional in the parent worktree.  If there is an uncommitted submodule (by this I mean the commit id into the submodule repo isn't committed into the parent repo) when doing a pull and submodule update, work could be lost as the subsequent submodule update may completely skip the prior submodule commit (since there is no conflict resolution against uncommitted submodules in the worktree).
* `gitr pull` will perform pull operations (instead of headless checkouts) in submodules if that submodule is checked out to a branch, merging from their tracking branch on the associated remote.  This leaves branches that users have made commits to recently in a branch-checkout state instead of a headless state, which is much more friendly for future commit generation.