#! /bin/sh
# $FreeBSD: mergemodules.sh,v 1.5 2003/02/28 18:38:30 peter Exp $

cd /r/synthcvs || exit 1

newmod=`mktemp /tmp/modules.XXXXXX`

cat << EOF > $newmod
# Synthetic merged CVS Modules File - machine generated, do not edit!
#
# \$FreeBSD\$
#
# Three different line formats are valid:
#	key	-a    aliases...
#	key [options] directory
#	key [options] directory files...
#
# Where "options" are composed of:
#	-i prog		Run "prog" on "cvs commit" from top-level of module.
#	-o prog		Run "prog" on "cvs checkout" of module.
#	-e prog		Run "prog" on "cvs export" of module.
#	-t prog		Run "prog" on "cvs rtag" of module.
#	-u prog		Run "prog" on "cvs update" of module.
#	-d dir		Place module in directory "dir" instead of module name.
#	-l		Top-level directory only -- do not recurse.
#
# NOTE:  If you change any of the "Run" options above, you'll have to
# release and re-checkout any working directories of these modules.
#
# And "directory" is a path to a directory relative to \$CVSROOT.
#
# The "-a" option specifies an alias.  An alias is interpreted as if
# everything on the right of the "-a" had been typed on the command line.
#
# You can encode a module within a module by using the special '&'
# character to interpose another module into the current module.  This
# can be useful for creating a module that consists of many directories
# spread out over the entire source repository.

# Convenient aliases
world			-a .

# CVSROOT support
CVSROOT		CVSROOT
access		CVSROOT access
avail		CVSROOT avail
commit_prep	CVSROOT commit_prep.pl
commitcheck	CVSROOT commitcheck
commitinfo	CVSROOT commitinfo
cvs_acls	CVSROOT cvs_acls.pl
cvsedit		CVSROOT cvsedit
cvswrappers	CVSROOT cvswrappers
editinfo	CVSROOT editinfo
log_accum	CVSROOT log_accum.pl
loginfo		CVSROOT loginfo
modules		CVSROOT modules
rcsinfo		CVSROOT rcsinfo
rcstemplate	CVSROOT rcstemplate
taginfo		CVSROOT taginfo
EOF

echo "" >> $newmod
echo "# ** MERGED FROM ncvs/CVSROOT/modules **"	>> $newmod
sed -n '/^# !!MERGE!!/,$p' < /r/ncvs/CVSROOT/modules | grep '^[0-9a-zA-Z]' | sort >> $newmod
echo "" >> $newmod
echo "# ** MERGED FROM pcvs/CVSROOT/modules **" >> $newmod
sed -n '/^# !!MERGE!!/,$p' < /r/pcvs/CVSROOT/modules | grep '^[0-9a-zA-Z]' | sort >> $newmod
echo "" >> $newmod
echo "# ** MERGED FROM dcvs/CVSROOT/modules **" >> $newmod
sed -n '/^# !!MERGE!!/,$p' < /r/dcvs/CVSROOT/modules | grep '^[0-9a-zA-Z]' | sort >> $newmod
echo "" >> $newmod
echo "# ** MERGED FROM projcvs/CVSROOT/modules **" >> $newmod
sed -n '/^# !!MERGE!!/,$p' < /r/projcvs/CVSROOT/modules | grep '^[0-9a-zA-Z]' | sort >> $newmod

#cat $newmod
#rm -f $newmod
#exit 0

rm -rf /r/synthcvs/modules
cvs -Q -R -d /r/FreeBSD.cvs checkout modules
cd modules || exit 1
lines=`diff -I '\$FreeBSD.*\$' $newmod modules | wc -l`
if [ $lines != 0 ]
then
  export DANGER=willrobinson
  cp $newmod modules
  cvs -Q commit -m 'Regenerated; Automated checkin' modules
fi
rm -f $newmod
