'''
Simplistic classes and functions for use only in specs
'''

class ClassWithNoArgs:
    ''' A class to instantiate with a no-arg constructor'''
    pass

class ClassWithOneArg:
    ''' A class to instantiate with a one-arg constructor'''
    def __init__(self, arg):
        pass

class ClassWithTwoArgs:
    ''' A class to instantiate with a two-arg constructor'''
    def __init__(self, arg1, arg2):
        pass

class _Parrot:
    ''' A class to use as an underlying system under test ''' 
    def is_dead(self):
        return False

class ClassWithSystemUnderTestMethod:
    ''' A class that wishes to expose an underlying sut '''
    def sut(self):
        return _Parrot() 
    
class ClassWithSystemUnderTestField:
    ''' Another class that wishes to expose an underlying sut '''
    def __init__(self):
        self.sut = _Parrot() 