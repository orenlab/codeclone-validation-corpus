class T0:
    pass


class T1:
    pass


class T2:
    pass


class T3:
    pass


class T4:
    pass


class T5:
    pass


class HighlyCoupled:
    def use0(self, value: T0) -> T0:
        self.t0 = T0()
        return value

    def use1(self, value: T1) -> T1:
        self.t1 = T1()
        return value

    def use2(self, value: T2) -> T2:
        self.t2 = T2()
        return value

    def use3(self, value: T3) -> T3:
        self.t3 = T3()
        return value

    def use4(self, value: T4) -> T4:
        self.t4 = T4()
        return value

    def use5(self, value: T5) -> T5:
        self.t5 = T5()
        return value
