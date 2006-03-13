#
# The do nothing makefile
#

OUTPUT=process.out


all:

protocol:
	@echo MakeProcessProtocol >${OUTPUT}

makecommand:
	@echo MakeCommand ${TEST1} ${TEST2} >${OUTPUT}

deinstall:
clean:

release:
	@echo ReleaseBuilder: ${BUILDNAME} ${CHROOTDIR} ${CVSROOT} ${RELEASETAG} ${NOPORTS} ${NODOC} ${MAKE_ISOS} >${OUTPUT}

package-recursive:
	@echo PackageBuilder: ${TEST1} ${TEST2} >${OUTPUT}

error:
	@echo Implosion >${OUTPUT}
	Implode here
