#! /bin/sh
# $FreeBSD: loglinks.sh,v 1.1 2003/02/27 23:10:25 peter Exp $
# Create a synthetic CVSROOT/commitlogs link farm in the traditional place

cd /r/FreeBSD.cvs/CVSROOT/commitlogs || exit 1

for repo in src doc ports projects
do
  for logfile in ../../CVSROOT-$repo/commitlogs/*
  do
    if [ ! -e "$logfile" ]
    then
      continue
    fi
    basename=`basename $logfile`
    case $basename in
    CVSROOT*)
	dirname=`dirname $logfile`
	ext=`expr "$basename" : "CVSROOT\(.*\)"`
	link="CVSROOT-$repo$ext"
	;;
    *)
        link=$basename
	;;
    esac
    if [ -L $link ]
    then
      oldlink=`/bin/ls -l $link | awk '{print $11}'`
      if [ "x$oldlink" = "x$logfile" ]
      then
	continue
      fi
    fi
    rm -f $link
    ln -sf $logfile $link
  done
done
for link in *
do
  if [ -L $link ]
  then
    oldlink=`/bin/ls -l $link | awk '{print $11}'`
    if [ ! -e $oldlink ]
    then
      rm -f $link
    fi
  fi
done
