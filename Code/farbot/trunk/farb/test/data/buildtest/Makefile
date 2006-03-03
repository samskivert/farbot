#
# The do nothing makefile
#

OUTPUT=process.out


all:

protocol:
	@echo MakeProcessProtocol >${OUTPUT}

makecommand:
	@echo MakeCommand ${TEST1} ${TEST2} >${OUTPUT}

release:
	@echo ReleaseBuilder: ${BUILDNAME} ${CHROOTDIR} ${CVSROOT} ${RELEASETAG} ${NOPORTS} ${NODOC} ${MAKE_ISOS} >${OUTPUT}

error:
	@echo Implosion >${OUTPUT}
	Implode here
