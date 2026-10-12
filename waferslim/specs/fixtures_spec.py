'''
BDD-style Lancelot specifications for the behaviour of the core library classes
'''
from waferslim.fixtures import EchoFixture

import lancelot

@lancelot.grouping
class EchoFixtureBehaviour:
    @lancelot.verifiable
    def echo_should_return_str_passed_in(self):
        echoer = lancelot.Spec(EchoFixture())
        echoer.echo('hello world').should_be('hello world')
        echoer.echo('1').should_be('1')

if __name__ == '__main__':
    lancelot.verify()
