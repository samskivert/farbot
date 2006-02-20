#
# The do nothing makefile
#

OUTPUT=make.out


all:

protocol:
	@echo MakeProcessProtocol >${OUTPUT}

makecommand:
	@echo MakeCommand ${TEST1} ${TEST2} >${OUTPUT}

release:
	@echo ReleaseBuilder: ${BUILDNAME} ${CHROOTDIR} ${CVSROOT} ${RELEASETAG} ${NOPORTS} ${NODOC} >${OUTPUT}

error:
	@echo Implosion >${OUTPUT}
	Implode here
