# utils.py vi:ts=4:sw=4:expandtab:
#
# Copyright (c) 2006 Three Rings Design, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. Neither the name of the copyright owner nor the names of contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from twisted.internet import reactor, defer

class ExecutionUnit(object):
    """
    An execution unit to be passed to an OrderedExecutor
    """
    def __init__(self, context, callable, *args, **kwargs):
        """
        Initialize an ExecutionUnit
        @param context: User-specified context
        @param callable: Callable function or method
        @param *args: Arguments to callable
        @param **kwargs: Keyword arguments to callable.
        """
        self.context = context
        self.callable = (callable, args, kwargs)

class OrderedExecutor(object):
    """
    Serialized execution of a list of deferred-returning callables
    according to the order in which they are added.
    """
    def __init__(self):
        self.eunits = []

    def appendExecutionUnit(self, eunit):
        """
        Append an ExecutionUnit to the end of the ordered list
        """
        self.eunits.append(eunit)

    def _callWorker(self):
        """
        Callable generator
        """
        for eunit in self.eunits:
            yield eunit.callable[0](*eunit.callable[1], **eunit.callable[2])

    def run(self):
        """
        Run all callables serially. Stop if an error occurs.
        @result A deferred that while fire when all callables have been run,
        or an error has occured.
        """
        d = defer.Deferred()
        work = iter(self._callWorker())

        # In our nested callback, iterate over callables returned by our
        # generator
        def cb(result):
            try:
                new = work.next()
            except StopIteration:
                # Iteration complete
                d.callback(None)
            else:
                # Add our nested callback to the new deferred
                new.addCallbacks(cb, d.errback)

        # Kick-off the looping deferred calls
        try:
            cb(None)
        except Exception, e:
            d.errback(e)

        return d
