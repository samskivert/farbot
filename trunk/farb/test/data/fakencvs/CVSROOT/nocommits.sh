#! /bin/sh
# $FreeBSD: nocommits.sh,v 1.7 2003/02/28 07:36:16 peter Exp $
#
# This is just some basic anti-foot-shooting to avoid accidental commits
# to cvsup'ed copies of the repository etc.

if [ "x`/bin/hostname`" = "xrepoman.freebsd.org" -a \
     "x$DANGER" = "xwillrobinson" ]
then
  exit 0
fi
echo "You are committing on the wrong repository!"
exit 1
